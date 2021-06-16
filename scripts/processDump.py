# -*- coding:utf8 -*-

""" 
Browse the dump file and search translated articles, according to explicit translation mark
When original version length in close to translated version's length, both content are saved, in raw text

Usage : python3 processDump.py [LANG]
Example : python3 processDump.py es

"""

import mwclient
from wiki_dump_reader import iterate
import pywikibot as pw
import re
import sys
import shelve
import os
import time
import urllib.parse

# INSTALL NOTE
# pywikibot : 
# 	pip3 install -U setuptools
# 	pip3 install pywikibot
# Then generate the user-config.py file. Getting in the pywikibot directory, run :
#	python3 pwb.py generate_user_files

### main parameters
targetLang='en'
translationRatio=1.05 # average increasement of word length due to translation
revisionStep=5
#nbOfDaysBetweenSourceIdAndTargetId=60
diffThreshold=0 # 0 for no threshold
recordAlignedFile=True
nBest=10


if len(sys.argv)==2 and len(sys.argv[1])==2:
	targetLang=sys.argv[1]
	
#~ wikidumpName='wiki-20201201-pages-articles-multistream.xml'
wikidumpName='wiki-20201220-pages-meta-current.xml'
wikidumpName='wiki-20201201-pages-meta-current.xml'
outputPath="/home/kraifo/Documents/WikipediaParaCorpus/data"
wordCountRef={ 
	'no':1702,
	'ee':2252,
	'ay':1019,
	'la':1313,
	'br':2048,
	'yo':3276,
	'bg':1755,
	'nl':1939,
	'uk':1595,
	'gl':1788,
	'sv':1691,
	'kg':2030,
	'da':1795,
	'ab':1322,
	'pl':1507,
	'lb':1983,
	'de':1616,
	'wo':1936,
	'ts':2402,
	'ro':1806,
	'en':1751,
	'so':1872,
	'pt':1846,
	'nn':1702,
	'mg':1974,
	'sw':1784,
	'eo':1585,
	'kk':1455,
	'cs':1500,
	'fi':1403,
	'fr':2037,
	'ku':1646,
	'id':1758,
	'ln':1792,
	'ja':294,
	'es':1927,
	'sr':1460,
	'ar':1368,
	'it':1917,
	'lv':1365,
	'sc':2153,
	'ca':1876,
	'ru':1586,
	'ko':1186,
	'lu':1857,
	'tr':1334,
	'mk':1720,
	'el':1881,
	'ks':2146,
	'lt':1439,
	'ms':1681,
	'uz':1749,
	'tl':2092,
	'hu':1510,
	'et':1390,
	'ht':2018,
	'nb':1635
}
	#~ "en-fr":1.14, # Hansard.fr/Hansard.en
	#~ "it-fr":1.06, # Bovary
	#~ "es-fr":1.06, # Bovary



log=open(outputPath+"/processDump."+targetLang+".log",mode="a",encoding="utf8")

mwSites={}

# constants

translationMarks={
	#~ 'fr':r'\{\{Traduction\/Référence',
	'fr':r'\{\{Traduit de\s*',
	'en':r'\{\{translated page\s*',
	'de':r'\{\{Übersetzung\s*',
	'it':r'\{\{Tradotto da\s*',
	'es':r'\{\{Traducido de\s*',
	'vi':r'\{\{Bài dịch\s*',
}

talkNameSpace={
	'fr':'Discussion',
	'en':'Talk',
	'de':'Diskussion',
	'it':'Discussione',
	'es':'Discusión',
	'vi':'Thảo luận'
}

supraCats={
	'fr':[
		'Catégorie:Article',
		'Catégorie:Accueil',
		'Catégorie:Espace encyclopédique',
		'Catégorie:Science',
		'Catégorie:Académie',
		'Catégorie:Vie humaine', 
		'Catégorie:Nature',
		'Catégorie:Discipline académique',
		'Catégorie:Humain',
		'Catégorie:Domaine scientifique',
		'Catégorie:Société',
		'Catégorie:Espace non encyclopédique',
		'Catégorie:Espace Wikipédia',
		'Catégorie:Relation humaine',
	],
	'en':[
		'Category:Articles',
	],
	'de':[
		'"‎Kategorie:Artikel‎"'
	]
}
		
superCats={
	'fr': {
		'arts': [
			'Catégorie:Architecture',
			'Catégorie:Artisanat',
			'Catégorie:Dessin',
			'Catégorie:Cinéma',
			'Catégorie:Design',
			'Catégorie:Littérature',
			'Catégorie:Musique',
			'Catégorie:Photographie',
			'Catégorie:Sculpture',
			'Catégorie:Arts du spectacle',
			'Catégorie:Artiste',
			'Catégorie:Histoire de l\'art',
			'Catégorie:Institution artistique',
			'Catégorie:Œuvre d\'art',
			'Catégorie:Technique artistique',
		],
		'societe':[
			'Catégorie:Alimentation',
			'Catégorie:Croyance',
			'Catégorie:Culture',
			'Catégorie:Divertissement',
			'Catégorie:Droit',
			'Catégorie:Éducation',
			'Catégorie:Idéologie',
			'Catégorie:Langue',
			'Catégorie:Médias',
			'Catégorie:Mode',
			'Catégorie:Organisation',
			'Catégorie:Groupe social',
			'Catégorie:Politique',
			'Catégorie:Santé',
			'Catégorie:Sexualité',
			'Catégorie:Sport',
			'Catégorie:Tourisme',
			'Catégorie:Travail',
			'Catégorie:Urbanisme'
		],
		'sciences':[
			'Catégorie:Astronomie',
			'Catégorie:Biologie',
			'Catégorie:Chimie',
			'Catégorie:Mathématiques',
			'Catégorie:Physique',
			'Catégorie:Sciences de la Terre',
			'Catégorie:Anthropologie',
			'Catégorie:Archéologie',
			'Catégorie:Économie',
			'Catégorie:Géographie',
			'Catégorie:Histoire',
			'Catégorie:Linguistique',
			'Catégorie:Information',
			'Catégorie:Philosophie',
			'Catégorie:Psychologie',
			'Catégorie:Sociologie'
		],
		'technologies':[
			'Catégorie:Aéronautique',
			'Catégorie:Agriculture',
			'Catégorie:Astronautique',
			'Catégorie:Électricité',
			'Catégorie:Électronique',
			'Catégorie:Énergie',
			'Catégorie:Industrie',
			'Catégorie:Ingénierie',
			'Catégorie:Informatique',
			'Catégorie:Mécanique',
			'Catégorie:Médecine',
			'Catégorie:Métallurgie',
			'Catégorie:Plasturgie',
			'Catégorie:Robotique',
			'Catégorie:Sylviculture',
			'Catégorie:Télécommunications',
			'Catégorie:Transports'
		],
		'espaceTemps':[
			'Catégorie:Chronologie',
			'Catégorie:Date',
			'Catégorie:Calendrier',
			'Catégorie:Siècle',
			'Catégorie:Année',
			'Catégorie:Événement'
			'Catégorie:Lieu',
			'Catégorie:Territoire',
			'Catégorie:Ville',
			'Catégorie:Continent',
			'Catégorie:Pays'
		],
		'personnalite':[
			'Catégorie:Par période historique',
			'Catégorie:Par métier',
			'Catégorie:Par secteur d\'activité',
			'Catégorie:Par nationalité' 
		]
	},
	'en':{
		'General reference':[
			'Category:Research',
			'Category:Library_science'
		],
		'Culture and the arts':[
			'Category:Culture',
			'Category:Humanities',
			'Category:Entertainment',
			'Category:Performing_arts',
			'Category:Visual_arts',
			'Category:Games',
			'Category:Toys',
			'Category:Sport',
			'Category:Recreation',
			'Category:Mass_media',
		],
		'Geography and places': [
			'Category:Geography',
			'Category:Places',
		],
		'Health and fitness': [
			'Category:Self_Care',
			'Category:Nutrition',
			'Category:Exercise',
			'Category:Hygiene',
			'Category:Positive_psychologie',
			'Category:Public_health',
			'Category:Health_science',
			'Category:Medecine'
		],
		'History and events': [
			'Category:History',
			'Category:Events',
		],
		'Human activities': [
			'Category:Human_activities',
		],
		'Natural and physical sciences': [
			'Category:Biology',
			'Category:Earth_sciences',
			'Category:Nature',
			'Category:Physical_sciences',
			'Category:Scientific_methods',
		],
		'People and self': [
			'Category:People',
			'Category:Personal_life',
			'Category:Self',
			'Category:Surnames',
		],
		'Philosophy and thinking': [
			'Category:Philosophy',
			'Category:Thought',
		],
		'Religion and belief systems': [
			'Category:Religion',
			'Category:Belief',
		],
		'Society and social sciences': [
			'Category:Society',
			'Category:Social_sciences',
		],
		'Technology and applied sciences': [
			'Category:Technology',
			'Category:Applied_sciences',
		],
	},
	"de":{
		"Sachsystematik":[
			"Kategorie:Räumliche Sachsystematik‎",
			"Kategorie:Zeitliche Sachsystematik‎",
			"Kategorie:Thema nach Organisation‎",
			"Kategorie:Thema nach Person‎",
			"Kategorie:Thema nach Sprache",
			"‎Kategorie:Bildung‎",
			"‎Kategorie:Digitale Welt",
			"‎Kategorie:Energiewesen",
			"‎Kategorie:Erde‎",
			"‎Kategorie:Ereignisse‎",
			"‎Kategorie:Feuer",
			"‎Kategorie:Fiktion",
			"‎Kategorie:Geographie",
			"‎Kategorie:Geschichte",
			"‎Kategorie:Geschlecht‎",
			"‎Kategorie:Gesellschaft‎",
			"‎Kategorie:Gesundheit",
			"‎Kategorie:Internationalität‎",
			"‎Kategorie:Kommunikation und Medien‎",
			"‎Kategorie:Kunst und Kultur",
			"‎Kategorie:Lebensstadien‎",
			"‎Kategorie:Lebewesen als Thema",
			"‎Kategorie:Methoden, Techniken und Verfahren",
			"‎Kategorie:Militärwesen",
			"‎Kategorie:Naturwissenschaft und Technik",
			"‎Kategorie:Organisationen‎",
			"‎Kategorie:Personen",
			"‎Kategorie:Planen und Bauen‎",
			"‎Kategorie:Politik",
			"‎Kategorie:Raum‎",
			"‎Kategorie:Recht‎",
		]
	}
}

# building topCats lists extracted from superCats tree
topCats={}

for language in superCats.keys(): 
	topCats[language]=[]
	for domain in superCats[language].keys():
		topCats[language].extend(superCats[language][domain])
	print("Language:",language,"=>",len(topCats[language]),"top categories")
			

parentCats={}




"""
wiki_dump_reader.Cleaner() is not used, because it removes hyperlink texts

cleaning rules

[[...|texte du lien à conserver]]
{{lien web| à supprimer}}
<ref>référence à supprimer</ref>
''à mettre entre guillemets''
{{balises à supprimer}}
{| tableaux à supprimer |}
{{date-|20 avril 1961}}

"""

regexCat=re.compile(r'\[\[\s*[KC]at\w+\s*:(.*?)\]\]')
regexLink=re.compile(r'\[\[(?:[^\[\]]*\|)?([^\[\]]+)\]\]',re.S)
regexBaliseAConserver=re.compile(r'\{\{(?:[^{}\n]*\|)([^|{}\n]*)\}\}',re.S)
regexBalise=re.compile(r'\{\{[^{}]*\}\}',re.S)
regexComment=re.compile(r'<!--[^>]*-->',re.S)
regexRef=re.compile(r'<ref\b.*?<\/ref>',re.S)
regexMarkup=re.compile(r'<[^>]*>',re.S)
regexTableau=re.compile(r'\{\|.*?\|\}',re.S)
regexEmptyLines=re.compile(r'\n\s*',re.S)
regexQuotes=re.compile(r"''",re.S)


def printLog(*msg):
	log.write(" ".join(msg)+"\n")
	print("\nlog > "+" ".join(msg))

# output a list of triples (lang,fileTitle,fileId)
# if no translation, list will be empty
def extractTranslationMark (text,regexTrans):
	m=regexTrans.search(text)
	result=[]
	if m:
		content=m.group(1)
		print("Translation mark:",content)
		# extraction of numerated info as lang1, art1, id1
		for i in range(1,5):
			mLang=re.search(r'lang'+str(i)+r'\s*=\s*(\w+)',content)
			if mLang:
				lang=mLang.group(1).lower()
				mArt=re.search(r'art'+str(i)+'\s*=\s*([^|]+)',content)
				if mArt:
					art=mArt.group(1)
				else:
					art=""
					printLog("Unreadable mark - no title:",content)
				mIdArt=re.search(r'lang'+str(i)+'\s*=\s*(\w+)',content)
				if mIdArt:
					idArt=mIdArt.group(1)
				else:
					idArt=""
					printLog("Unreadable mark - no id:",content)
				result.append((lang,art,idArt))
			else:
				break
		# german model
		mIso=re.search(r'ISO\s*=\s*(\w\w)',content,re.I)
		mFremdlemma=re.search(r'FREMDLEMMA\s*=\s*([^|}\n]+)',content,re.I)
		if mIso and mFremdlemma:
			lang=mIso.group(1).lower()
			art=mFremdlemma.group(1)
			idArt=""
			mFremdrevid=re.search(r'FREMDREVID\s*=\s*(\d+)',content,re.I)
			if mFremdrevid:
				idArt=mFremdrevid.group(1)
			idTgt=""
			mRevid=re.search(r'REVID\s*=\s*(\d+)',content,re.I)
			if mRevid:
				idTgt=mRevid.group(1)
			result.append((lang,art,idArt,idTgt))	
		
		# extraction of not numerated implicit info
		# en, fr, it
		if len(result)==0:
			m=re.search(r'^\s*\|\s*(\w\w)\s*\|\s*([^|]+)(.*)',content)
			if m:
				lang=m.group(1).lower()
				art=m.group(2)
				rest=m.group(3)
				mIdArt=re.search(r'(?:3=|\b(?:version|oldid|phiên bản)\s*=)?\s*(\d\d\d\d\d+)',rest)
				idArt=""
				if mIdArt:
					idArt=mIdArt.group(1)
				else:
					printLog("Unreadable id:",content)
				idTgt=""
				mRevid=re.search(r'(?:insertversion|phiên bản Việt)\s*=\s*(\d+)',content,re.I)
				if mRevid:
					idTgt=mRevid.group(1)
				result.append((lang,art,idArt,idTgt))	
			else:
				printLog("Unreadable mark:",content)

	return result

# text cleaning
def clean(text) :
	if text:
		text=regexCat.sub('',text)
		text=regexLink.sub('\g<1>',text)
		# suppression des balises en plusieurs temps, car elles sont possiblement imbriquées jusqu'à 3 niveaux
		text=regexBaliseAConserver.sub('\g<1>',text)
		text=regexComment.sub('',text)
		text=regexBalise.sub('',text)
		text=regexBalise.sub('',text)
		text=regexBalise.sub('',text)
		text=regexBalise.sub('',text)
		text=regexLink.sub('\g<1>',text)
		
		text=regexTableau.sub('',text)
		text=regexRef.sub('',text)
		text=regexEmptyLines.sub("\n",text)
		text=regexQuotes.sub('"',text)
		
		return text
	else:
		return ""

# function that uses mwclient to retrieve a given revision
def getArticleByTitleAndId(site,title,articleId):
	try :
		page=mwclient.page.Page(site,urllib.parse.unquote(title)).resolve_redirect()
	except:
		printLog("Error : impossible to download article:",urllib.parse.unquote(title))
		return ("",0)
	
	# looking for revision that corresponds to recherche des révisions correspondant à articleId
	revs=page.revisions(startid=articleId,endid=articleId,prop='content|timestamp')
				
	try :
		rev=revs.next()
		if '*' in rev.keys(): 
			return (str(rev['*']),rev['timestamp'])
		else:
			return (str(page.text()),0)
	except :
		# when articleId is null return here
		return (str(page.text()),0)

def getArticleByTitleAndTimestamp(site,title,timestamp):
	try :
		page=mwclient.page.Page(site,urllib.parse.unquote(title)).resolve_redirect()
	except:
		printLog("Error : impossible to download article:",urllib.parse.unquote(title))
		return ""
	
	# looking for revision that corresponds to recherche des révisions correspondant à articleId
	revs=page.revisions(start=timestamp,dir='older',prop='content')
				
	try :
		rev=revs.next()
		if '*' in rev.keys(): 
			return str(rev['*'])
		else:
			return page.text()
	except :
		# when timestamp is null return here
		return page.text()

# function that uses mwclient to retrieve the current version
def getArticleByTitle(site,title):
	try :
		page=mwclient.page.Page(site,urllib.parse.unquote(title)).resolve_redirect()
		return page.text()
	except:
		printLog("Error : impossible to download article:",title)
		return ""

# search the revision history in order to find the first version that corresponds to the translation
def getFirstRevisionWithTranslationMarkup(firstRevisionIdHash,targetTitle,page,translationMark,sourceTitle,timestamp):
	articleId=""
	if targetTitle in firstRevisionIdHash.keys():
		articleId=firstRevisionIdHash[targetTitle]
		print("first revision id is",articleId)
		revs=page.revisions(prop='content|ids|timestamp',startid=articleId,endid=articleId)
	elif timestamp :
		revs=page.revisions(prop='content|ids|timestamp',start=timestamp,dir='newer') # end=time.gmtime(time.mktime(timestamp)+nbOfDaysBetweenSourceIdAndTargetId*3600*24))
	else:
		revs=page.revisions(prop='content|ids|timestamp',dir='newer')
	
	currentId=""
	currentTimestamp=""
	try :
		# iterating revisions from older to newer
		for rev in revs : 
			if '*' in rev.keys():
				currentId=str(rev['revid'])
				currentTimestamp=rev['timestamp']
				# when the translation markup is found break
				if  re.search(translationMark+'[^}]*'+sourceTitle+r'[^}]*\}\}',rev['*']):
					break
			# stepping forward of 20 revisions
			count=0
			while count<revisionStep:
				count+=1
				if '*' in rev.keys():
					currentId=str(rev['revid'])
					currentTimestamp=rev['timestamp']
				try: 
					rev=revs.next()
				except:
					break
	except:
		printLog("Error while retrieving first revision for",targetTitle)
		return 0
	if currentId and not articleId :
		firstRevisionIdHash[targetTitle]=currentId
	return currentTimestamp

# basic word counting
def countWords(text):
	words=re.findall(r'\w+',text,re.U)
	return len(words)

# category management

def findParentCat(parentCats,pwSite,myPage):
	if not myPage in parentCats.keys():
		parentCats[myPage]=[
			cat.title()
			for cat in pw.Page(pwSite, myPage).categories()
			if 'hidden' not in cat.categoryinfo
		]
		
	return parentCats[myPage]

def findSuperCats(topCats,supraCats,parentCats,pwSite,myPage):
	# on crée des listes de catégories enregistrant la fréquence associée à chaque cat.
	currentList={}
	# initialement on n'a qu'une page, avec une fréquence 1
	currentList[myPage]=1
	loop=True
	nLoop=0
	while loop:
		nLoop+=1
		if nLoop > 100:
			break
		loop=False
		newList={}
		# pour chaque page de la liste courante, on cherche ses parents
		for page in currentList.keys():
			parents=findParentCat(parentCats,pwSite,page)
			# si la cat. a des parents en dehors des supraCats
			if parents and parents[0] not in supraCats:
				# dans la nouvelle liste on substitue chaque page par ses parents, qui héritent de sa fréquence
				for parent in [page for page in parents if not page in supraCats]:
					if parent in newList.keys():
						newList[parent]+=currentList[page]
					else:
						newList[parent]=currentList[page]
				# quand il y a eu substitution, on reboucle
				loop=True
			else:
				if parents:
					# les pages filles des supracats ne bougent plus
					newList[page]=currentList[page]
		
		# si la liste des supraCats n'est pas complète, on peut atteindre une liste stable
		# il faut donc sortir de la boucle
		if " ".join(sorted(currentList.keys())) == " ".join(sorted(newList.keys())):
			loop=False

		topCateg=[cat for cat in newList.keys() if cat in topCats]
		if topCateg:
			for cat in topCateg:
				currentList[cat]=newList[cat]
			break
		else:
			sortedCats=list(newList.keys())
			sortedCats.sort(reverse=True,key=lambda x: newList[x])
			for cat in sortedCats[0:nBest]:
				currentList[cat]=newList[cat]
	
	sortedCats=list(currentList.keys())
	sortedCats.sort(reverse=True,key=lambda x: currentList[x])		
	
	return sortedCats

def calcDiff(nWords1,nWords2,LangRatio):
	if nWords1!=0 or nWords2!=0:
		return 2*(nWords1/translationRatio-nWords2/LangRatio)/(nWords1/translationRatio+nWords2/LangRatio)
	else:
		return 10000


def wordLengthDiffMatches(wordLengthDiff):
	if abs(wordLengthDiff) > 0.25:
		return True
	else:
		return False
		
	if diffThreshold==0:
		return True
	return (wordLengthDiff >= -1* diffThreshold and wordLengthDiff <= diffThreshold)
	
#**************************************************************************** 
# arg1 : processedPages - a hash (recorded in a shelve) that record the title of the already processed pages for a given dump
# arg2 : mwSites - a hash containing the mwclient.Site objects for each language
# arg3 : stats - a hash (recorded in a shelve) containing the stats (word numbers and article numbers) for [target][source] language pairs
# arg3 : statsPerCat - a hash (recorded in a shelve) containing the stats (word numbers) for [target][source] language pairs
# arg4 : firstRevisionIdHash - a hash containing, for a given title, the id of the first revision that contains the translation
# arg5 : parentCats - a hash, recorded in a shelves, recording the parent categories for each article / category page
# arg6 : targetLang - a string (e.g. 'fr') which indicates the language of the dump.xml file to process
# arg7 : wordLengthDiffFile - a file to record all diff in order to study the diff distribution

def processDump(processedPages,mwSites,stats,statsPerCat,firstRevisionIdHash,parentCats,targetLang,wordLengthDiffFile):
	n=0
	
	# loading the site objects
	mwSites[targetLang] = mwclient.Site(targetLang+'.wikipedia.org')
	pwSite=pw.Site(targetLang, 'wikipedia')
	
	regexTrans=re.compile(translationMarks[targetLang]+r'(.*?)\}\}',flags=re.S|re.I)
	
	# iterating over dump in target language
	# NB : iterate function has been modified to cover all the namespaces
	for targetTitle, targetText in iterate(targetLang+wikidumpName):
		n+=1
		if n % 10000 == 0:
			print (n,targetTitle)
		
		# selection of Talk page
		m= re.match(talkNameSpace[targetLang]+r'\s*:(.*)',targetTitle)
		talkTitle=targetTitle
		if m:
			targetTitle=m.group(1)
			textWithMark=targetText
			if targetTitle in processedPages.keys():
				# if already processed : skip and jump to next page
				continue
		else:
			# if not a talk page : skip and jump to next page
			continue
		
		# looking for translation mark
		triples=extractTranslationMark(textWithMark,regexTrans)
		
		# if a translation mark has been found
		if triples:
			# loading the Page object (mwclient)
			try:
				page=mwclient.page.Page(mwSites[targetLang],urllib.parse.unquote(targetTitle)).resolve_redirect()
				cleanedTargetText=clean(page.text())
			except:
				print("Error while downloading page",targetTitle)
				continue
	
			# Searching current article ID
			revs=page.revisions(prop="ids",dir='older')
			try:
				rev=revs.next()
				targetId=str(rev['revid'])
			except:
				targetId=""

			printLog('page',str(n),':',targetTitle,"("+targetId+")")
			if targetLang in topCats.keys():
				superCats=findSuperCats(topCats[targetLang],supraCats[targetLang],parentCats,pwSite,targetTitle)
			else:
				superCats=findParentCat(parentCats,pwSite,targetTitle)
			
			# for each source 
			for triple in triples:
				sourceLang=triple[0]
				sourceTitle=triple[1]
				sourceId=triple[2]
				revId=0
				# dans le cas où revId est indiqué (allemand) on charge la bonne révision
				if len(triple)==4:
					revId=triple[3]
					if revId:
						revs=page.revisions(prop='content|ids',startid=revId,dir='newer')
						try:
							rev=revs.next()
							cleanedTargetText=clean(rev['*'])
							print("Using revId=",revId)
						except:
							print("Bad revId=",revId)
				if len(sourceLang)<=3:

					# looking for source page
					if not sourceLang in mwSites.keys():
						print("Opening",sourceLang+'.wikipedia.org')
						try:
							mwSites[sourceLang]= mwclient.Site(sourceLang+'.wikipedia.org')
						except:
							printLog("impossible to load wiki for language",sourceLang)

					# recording the text pair if length matches
					if sourceLang in mwSites.keys():
						(sourceText,timestamp)=getArticleByTitleAndId(mwSites[sourceLang],sourceTitle,sourceId)
						cleanedSourceText=clean(sourceText)
						# words2 = source, words1 = target
						nWords2=countWords(cleanedSourceText)
						nWords1=countWords(cleanedTargetText)
						if nWords2==0 and nWords1==0:
							printLog("Error : 0 length texts")
							continue
						
						langRatio=1
						if sourceLang in wordCountRef.keys() and targetLang in wordCountRef.keys():
							langRatio=wordCountRef[sourceLang]/wordCountRef[targetLang]
						wordLengthDiff=calcDiff(nWords1,nWords2,langRatio)  
						
						# if revId is unknown and  the word length are two different, looking for the first revision with translation
						if abs(wordLengthDiff)>0.15 and revId==0:
							# looking for initial version of translation
							#~ print("Searching initial version of translation")
							
							talkPage=mwclient.page.Page(mwSites[targetLang],urllib.parse.unquote(talkTitle)).resolve_redirect()
							firstRevisionTimestamp=getFirstRevisionWithTranslationMarkup(firstRevisionIdHash,talkTitle,talkPage,translationMarks[targetLang],sourceTitle,timestamp)
							
							if firstRevisionTimestamp:
								revs=page.revisions(prop='content|ids|timestamp',start=firstRevisionTimestamp,dir='newer') 
								#~ print("Timestamp",firstRevisionTimestamp)
								try :
									rev=revs.next()
									firstRevisionText=rev['*']
									initTargetText=clean(firstRevisionText)
									if initTargetText!="":
										cleanedTargetText=initTargetText
									nWords1=countWords(cleanedTargetText)
									
									# get initial version ID
									if targetTitle in firstRevisionIdHash.keys():
										targetId=firstRevisionIdHash[targetTitle]
									
									# if the first revision has a timestamp than it is possible to find the corresponding version of source text
									if not sourceId and firstRevisionTimestamp:
										sourceText=getArticleByTitleAndTimestamp(mwSites[sourceLang],sourceTitle,firstRevisionTimestamp)
										cleanedSourceText=clean(sourceText)
										nWords2=countWords(cleanedSourceText)
										printLog("A corresponding version of source text has been found !")
									if nWords2==0 and nWords1==0:
										printLog("Error : 0 length texts")
										continue
									wordLengthDiff= calcDiff(nWords1,nWords2,LangRatio)
								except :
									printLog("Failed to find first revision")

								
						# UPDATING stats
						# simple statistics of link counts by source language
						if not (sourceLang) in stats.keys():
							stats[sourceLang]=0
						stats[sourceLang]+=1

						# updating statsPerCat
						if not (sourceLang+"\t*") in statsPerCat.keys():
							statsPerCat[sourceLang+"\t*"]=0
						statsPerCat[sourceLang+"\t*"]+=nWords1/len(triples)
						#~ print("Searching top categories")
						for cat in superCats:
							if (sourceLang+"\t"+cat) not in statsPerCat.keys():
								statsPerCat[sourceLang+"\t"+cat]=0
							statsPerCat[sourceLang+"\t"+cat]+=nWords1/len(triples)
							#~ printLog(sourceLang+"\t"+cat+"\t"+str(nWords1)+"\t"+str(len(triples)))
						# mark the page as processed
						processedPages[targetTitle]=1
					

						wordLengthDiffFile.write(str(wordLengthDiff)+"\n")
						printLog(sourceLang,"->",targetLang," : wordLengthDiff="+str(wordLengthDiff))
						
						# if diff between word lengths is under 25%, files will be recorded
						if wordLengthDiffMatches(wordLengthDiff) and recordAlignedFile:
							name=sourceTitle
							name=re.sub(r'[?():!."\'<>\/*+]','_',name)
							print ("Recording",name,"for",sourceLang+"-"+targetLang)
							
							outPath=outputPath+"/"+sourceLang+"-"+targetLang+"/"
							if not os.path.isdir(outPath):
								os.mkdir(outPath)
							
							with open(outPath+name+".2."+sourceLang+".txt",encoding='utf8',mode='w') as src_out:
								src_out.write("Title:"+sourceTitle+"\n")
								src_out.write("Id:"+sourceId+"\n")
								src_out.write(cleanedSourceText)
							with open(outPath+name+".2."+targetLang+".txt",encoding='utf8',mode='w') as tgt_out:
								tgt_out.write("Title:"+targetTitle+"\n")
								tgt_out.write("Id:"+targetId+"\n")
								tgt_out.write(cleanedTargetText)
	return n

#**************************************************************** MAIN

with shelve.open(outputPath+'/parentCats.'+targetLang) as parentCats:
	with shelve.open(outputPath+'/statsPerCat.'+targetLang) as statsPerCat:
		with shelve.open(outputPath+'/stats.'+targetLang) as stats:
			with shelve.open(outputPath+'/processed.'+targetLang) as processedPages:
				with shelve.open(outputPath+'/firstRevisionId.'+targetLang) as firstRevisionIdHash:
					with open(outputPath+'/wordLengthDiff.'+targetLang+".txt",mode='a') as wordLengthDiffFile:
						wordLengthDiffFile.write("------------------------------------\n")
						n=processDump(processedPages,mwSites,stats,statsPerCat,firstRevisionIdHash,parentCats,targetLang,wordLengthDiffFile)
						print(n,"pages has been processed!")
						#~ for lang_cat in statsPerCat.keys():
						#~ 	print (lang_cat,"=>",statsPerCat[lang_cat])

log.close()
    

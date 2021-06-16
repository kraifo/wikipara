# -*- coding:utf8 -*-

import os
import sys
import re
import matplotlib.pyplot as plt
import math
import argparse
import array
import time


# reading the command line arguments
parser = argparse.ArgumentParser(
	prog='alignable',
	formatter_class=argparse.RawDescriptionHelpFormatter,
	description='''\
A program that select alignable sentences for parallel text pairs. 
	
Input : the corresponding files must be named following this pattern : NAME.L1.txt NAME.L2.txt
	
Files should be formatted as raw utf8 text with one sentence per line.
The output will yield a new pair of files that contain a selection of 
sentences in TXT, CES or ARC format, in order to be easily aligned
in a next step (the non parallel text is supposed to be removed).
'''
)

parser.add_argument('-v','--verbose',help='Verbose messages',action="store_true")
parser.add_argument('-V','--veryVerbose',help='Very verbose messages',action="store_true")
parser.add_argument('-p','--printPlot',help='Print scatter plot',action="store_true")
parser.add_argument('-i','--inputFormat',help='Format of the input (txt or arc)',default="txt")
parser.add_argument('-o','--outputFormat',help='Format of the output',default="ces")
parser.add_argument('--inputDir', type=str, help='The directory to process', default='.')
parser.add_argument('--outputDir', type=str, help='The directory to save output files', default='./alignable')
parser.add_argument('--l1', type=str, help='The source language (ISO : ex. "en" for English)', default='en')
parser.add_argument('--l2', type=str, help='The target language (ISO : ex. "fr" for French)', default='fr')
parser.add_argument('-f','--filePattern', type=str, help='The pattern of the files that should be processed. A capturing group such as (.*) should capture the common prefix between aligned files.', default=r'(.*)[.]\w\w[.]\w+$')
parser.add_argument('-n','--ngram', type=int, help='The ngram size', default=4)
parser.add_argument('-d','--diceThreshold', type=float, help='The minimum dice score to yield a candidate point', default=0.05)
parser.add_argument('-k','--kBest', type=int, help='Number of the best coordinates for each line ore column to keep when creating points', default=4)
parser.add_argument('-x','--deltaX', type=int, help='Local space definition : +/-delta X on horizontal axis', default=12)
parser.add_argument('-y','--deltaY', type=int, help='Local space definition : +/-delta Y on vertical axis', default=2)
parser.add_argument('-H','--minHorizontalDensity', type=float, help='The minimal horizontal density in a interval to be kept in the final result', default=0.2)
parser.add_argument('-m','--maxDistToTheDiagonal', type=int, help='The maximal distance to the diagonal (inside a given interval) for a point to be taken into account in the horizontal density', default=4)
parser.add_argument('-D','--minDensityRatio', type=float, help='The minimal local density ratio (reported to the average local density) to keep a candidate point', default=0.5)
parser.add_argument('-g','--maxGapSize', type=int, help='The maximal distance between to consecutive points in the same interval', default=10)


args = parser.parse_args()

# generic parameters
l1=args.l1
l2=args.l2
verbose=args.verbose
veryVerbose=args.veryVerbose
filePattern=re.compile(args.filePattern)
printPlot=args.printPlot
inputDir=args.inputDir
outputDir=args.outputDir
inputFormat=args.inputFormat
outputFormat=args.outputFormat

# ngram identification
n=args.ngram 				# ngram size
diceThreshold=args.diceThreshold	# min dice to add a candidate point

# filtering parameters
deltaX=args.deltaX			# local space definition : +/-delta X on horizontal axis
deltaY=args.deltaY			# local space definition : +/-delta Y on vertical axis
minDensityRatio=args.minDensityRatio			# the minimal local density ratio (relatively to the average local density) to keep a candidate point
minHorizontalDensity=args.minHorizontalDensity 	# the minimal density on horizontal axis to keep an interval in the final result
maxDistToTheDiagonal=args.maxDistToTheDiagonal 	# the maximal distance to the diagonal (inside a given interval) for a point to be taken into account in the horizontal density
kBest=args.kBest			# number of best coordinates to keep in creating points
maxGapSize=args.maxGapSize	# max distance between two points to make a gap between two interval

# useless parameters ?
minSentLengthRatio=0.2	# the minimal ratio between the shorter and the longer sentence to yield a candidate point
minSentLength=1			# the minimal sentence size to look for ngram

diagWidth=0 # width of the search space around the diag. If 0 : all the space is searched

# direct settings

#~ l1="en"
#~ l2="fr"
#~ inputDir="/home/kraifo/Documents/Recherches/Publis/Revues - Ouvrages collectifs/2021 Benjamins - Wikipedia as a corpus/align_test/"+l1+"-"+l2+"/seg"
#~ outputDir="/home/kraifo/Documents/Recherches/Publis/Revues - Ouvrages collectifs/2021 Benjamins - Wikipedia as a corpus/align_test/"+l1+"-"+l2+"/seg/alignable"
#~ verbose=True
#~ inputFormat="arc"
#~ outputFormat="arc"
#~ filePattern=re.compile("(.*).\w\w.\w\w\w$")
#~ printPlot=True
#~ n=4

# Settings for novels or big documents

#~ diceThreshold=0.02
#~ diagWidth=100 
#~ minDensityRatio=0.3
#~ minHorizontalDensity=0.005
#~ maxGapSize=400
#~ deltaX=15
#~ deltaY=4

########################################

arcHeader="\n<text>\n<divid='d1'>\n<pid='d1p1'>\n"
arcFooter="</p>\n</div>\n</text>\n"

cesHeader="""<?xml version="1.0" encoding="utf-8"?>
<cesAna>
<chunkList>
<chunk>
<par>
"""
cesFooter="""
</par>
</chunk>
</chunkList>
</cesAna>"""


# computation of local density 
def computeLocalDensity(i,j,points,I,J):
	localSpaceSize=0
	nbPointsInLocalSpace=0
	for X in range(max(0,i-deltaX),min(i+deltaX+1,I)):
		for Y in range(max(0,j-(i-X)-deltaY),min(j-(i-X)+deltaY+1,J)):
			localSpaceSize+=1
			if (X,Y) in points.keys():
				nbPointsInLocalSpace+=1
	return nbPointsInLocalSpace/localSpaceSize

# filtering points by eliminating every point in the center of a low density local area
def filterPoints(points,I,J,averageDensity):
	# initialisation of filtered points
	x_filtered=[]
	y_filtered=[]
	nbDeleted=0
	
	if veryVerbose:
		print("Filtering ",len(points),"...")

	# computation of local density for each point
	pointsKey=sorted(list(points.keys()),key=lambda point:point[0])
	
	for point in pointsKey:
		(i,j)=point
		
		localDensity=computeLocalDensity(i,j,points,I,J)
		
		if veryVerbose:
			print ("i=",i,"j=",j,"Local density=",localDensity,"Average density=",averageDensity,"Ratio=",round(localDensity/averageDensity,2))
		
		# point is removed if density is not high enough
		if localDensity/averageDensity < minDensityRatio:
			del(points[(i,j)])
			nbDeleted+=1
		else:
			x_filtered.append(i)
			y_filtered.append(j)
	
	if verbose:
		print(nbDeleted,"points have been removed!")
	
	return (x_filtered,y_filtered)

# removing points that are conflicting on the same column : only the point with the higher local density is kept
def resolvingConflicts(points,I,J):
	x2y={}
	x_filtered=[]
	y_filtered=[]
	nbDeleted=0
	pointsKey=list(points.keys())
	for point in pointsKey:
		(i,j)=point
		if i in x2y.keys():
			# for x coordinate, conflict between (i,j) and (i,x2y[i])
			# only the best point is kept
			density1=computeLocalDensity(i,j,points,I,J)
			density2=computeLocalDensity(i,x2y[i],points,I,J)
			if density1 > density2:
				del(points[(i,x2y[i])])
				x2y[i]=j
			else:
				del(points[(i,j)])
			nbDeleted+=1	
		else:
			x2y[i]=j
	if verbose:
		print(nbDeleted,"conflicting points have been removed!")
	
	pointsKey=list(points.keys())
	for point in pointsKey:
		(i,j)=point
		x_filtered.append(i)
		y_filtered.append(j)
	return (x_filtered,y_filtered)

# ngram that contain only the same repeated character are not valid (e.g. blank spaces...)
def valid(ngram):
	return not re.match(r'(.)\1+',ngram)


#************************************************************************* MAIN

if __name__ == "__main__":
	t0=time.monotonic()
	
	# reading aligned files
	for file1 in os.listdir(inputDir):
		m=filePattern.match(file1)
		if m and re.search(l1+"."+inputFormat,file1,re.I):
			# processing of an aligned file pair
			name=m.group(1)
			file2=name+"."+l2+"."+inputFormat
			if verbose: 
				print("Processing",file1,"and",file2)
			f1=open(os.path.join(inputDir,file1),encoding='utf8')
			f2=open(os.path.join(inputDir,file2),encoding='utf8')
			sents1=[]
			sents2=[]
			idSents1=[]
			idSents2=[]
			lenSents1=0
			lenSents2=0
			if inputFormat=="arc" or inputFormat=="ces":
				sentId=""
				for line in f1:
					line=line.strip()
					m=re.search(r'<s\s+id="([^"]*)"',line)
					if m:
						sentId=m.group(1)
					elif sentId!="":
						idSents1.append(sentId)
						sents1.append(line)
						lenSents1+=1
						sentId=""
				for line in f2:
					line=line.strip()
					m=re.search(r'<s\s+id="([^"]*)"',line)
					if m:
						sentId=m.group(1)
					elif sentId!="":
						idSents2.append(sentId)
						sents2.append(line)
						lenSents2+=1
						sentId=""
			else:
				for line in f1:
					line=line.strip()
					sents1.append(line)
					lenSents1+=1
				for line in f2:
					line=line.strip()
					sents2.append(line)
					lenSents2+=1

			# extracting hash table that records all the ngrams for sents1
			ngrams1=[]
			for i in range(lenSents1):
				ngrams1.append({})
				sent1=sents1[i]
				for k in range(0,len(sent1)-n):
					ngram=sent1[k:k+n]
					if valid(ngram):
						if ngram not in ngrams1[i].keys() :
							ngrams1[i][ngram]=0
						ngrams1[i][ngram]+=1

			# extracting hash table that records all the ngrams for sents2
			ngrams2=[]
			for j in range(lenSents2):
				sent2=sents2[j]
				ngrams2.append({})
				for k in range(0,len(sent2)-n):
					ngram=sent2[k:k+n]
					if valid(ngram):
						if ngram not in ngrams2[j].keys():
							ngrams2[j][ngram]=0
						ngrams2[j][ngram]+=1
			
			# record the corresponding coordinate, sorted according to dice
			bestJ={}
			bestI={}

			# 
			if diagWidth:
				range2=diagWidth
			else : 
				range2=lenSents2
			# dice computation for each point (i,j)
			for i in range(lenSents1):
				nb1=max(1,len(sents1[i])-n+1)
				if verbose and i%100==0:
					print ("x =",i,"/",lenSents1)
				for J in range(range2):
					if diagWidth:
						# when using fixed vertical width around diag, j must be computed as: int(i*lenSents2/lenSents1-range2/2)
						j=int(i*lenSents2/lenSents1-range2/2)
					else:
						j=J
					if j<0:
						continue
					nb2=max(1,len(sents2[j])-n+1)
					# length of sent1 and sent2 must be comparable
					if nb1>minSentLength and nb2>minSentLength and nb1/nb2 >= minSentLengthRatio and nb2/nb1 >=minSentLengthRatio:
						# computing the number of common ngrams (based on occurrences and not on type)
						nbCommon=0
						for ngram in ngrams1[i].keys():
							if ngram in ngrams2[j].keys():
								nbCommon+=min(ngrams1[i][ngram],ngrams2[j][ngram])
						dice=2*nbCommon/(nb1+nb2)
						# if dice is greater than the threshold, candidate point (i,j) is recorded
						if dice>diceThreshold:
							if not j in bestI.keys():
								bestI[j]=[]
							if not i in bestJ.keys():
								bestJ[i]=[]
							bestI[j].append((dice,i))
							bestJ[i].append((dice,j))

			# building the point list taking, for each coordinate, the k best corresponding point
			x=[]
			y=[]
			points={} # points are recorded here as keys
			for i in bestJ.keys():
				# sorting the candidate according to dice
				bestJ[i]=sorted(bestJ[i],key = lambda x:x[0],reverse=True)
				# only the k best are recorded
				bestJ[i]=[bestJ[i][l][1] for l in range(0,min(kBest,len(bestJ[i])))]
				
			for j in bestI.keys():
				# sorting the candidate according to dice
				bestI[j]=sorted(bestI[j],key = lambda x:x[0],reverse=True)
				# only the k best are recorded
				bestI[j]=[bestI[j][l][1] for l in range(0,min(kBest,len(bestI[j])))]
			
			for i in bestJ.keys():	
				for j in bestJ[i]:
					if i in bestI[j]:
						x.append(i)
						y.append(j)
						points[(i,j)]=1

			# compute average local density around selected points
			pointsKey=list(points.keys())
			if len(pointsKey)==0:
				continue

			totDensity=0
			for point in pointsKey:
				(i,j)=point
				totDensity+= computeLocalDensity(i,j,points,lenSents1,lenSents2)
			
			averageDensity=totDensity/float(len(pointsKey))
		
		
			# filtering
			(x_filtered,y_filtered)=filterPoints(points,lenSents1,lenSents2,averageDensity)
			(x_filtered,y_filtered)=resolvingConflicts(points,lenSents1,lenSents2)
			
			# finding aligning interval
			beginInt=(0,0)
			lastI=0
			lastJ=0
			intervals=[] # the array of pairs (beginInt,endInt) where beginInt and endInd are two points that define the interval
			nbInInterval=0
			totalIntervalLength=0
			lastDensity=computeLocalDensity(0,0,points,lenSents1,lenSents2)
			for num in range(0,len(x_filtered)):
				(i,j)=(x_filtered[num],y_filtered[num])
				print(i,j)
				density=computeLocalDensity(i,j,points,lenSents1,lenSents2)
				# computation of the distance between (i,j) and (i,expected(j)) 
				expectedJ=lastJ+(i-lastI)
				dist=abs(j-expectedJ)

				# only the points that are near the diagonal are taken into account
				if dist <= maxDistToTheDiagonal:
					nbInInterval+=1
				else:
					print("not in Interval. Density",density,"last density",lastDensity)
					# anomalous points are not taken into account in the interval computation
					if lastDensity> 0 and density/lastDensity<0.5:
						continue
					
				# computing distance
				d=math.sqrt((i-lastI)**2+(j-lastJ)**2)
				# if a there is a gap, the previous interval is closed and a new interval will begin
				if d>maxGapSize:
					print("maxGapSize")
					endInt=(lastI,lastJ)
					if beginInt[0]<lastI and beginInt[1]<lastJ:
						# to save the interval, we compute the density of selected points according to the horizontal width
						if nbInInterval/(lastI - beginInt[0]) >= minHorizontalDensity and nbInInterval>1:
							intervals.append((beginInt,endInt))
							totalIntervalLength+=lastI - beginInt[0]
						else:
							if verbose:
								print("Interval",beginInt,endInt,"has been discarded (density too low)")
					beginInt=(i,j)
					nbInInterval=0
				lastI=i
				lastJ=j
				lastDensity=density
			
			if lastI!=beginInt[0]:
				intervals.append((beginInt,(lastI,lastJ)))
				totalIntervalLength+=lastI - beginInt[0]

			if verbose:
				print("Total interval length=",totalIntervalLength)
			# display of the points : eliminated points are red
			if printPlot:
				plt.axis([1,lenSents1,1,lenSents2])
				plt.title(name+'.'+l1+'-'+l2+'.txt - filtered')
				plt.scatter(x,y,c="red",s=1)
				plt.scatter(x_filtered,y_filtered,c="black",s=1)
				for interval in intervals:
					(i1,j1)=interval[0]
					(i2,j2)=interval[1]
					x=[i1,i1,i2,i2,i1]
					y=[j1,j2,j2,j1,j1]
					plt.plot(x,y,c="grey")
				plt.show()
				plt.close()
			
			# writing output files
			if len(intervals)>0:
				if not os.path.exists(outputDir):
					os.mkdir(outputDir)
				output1=open(os.path.join(outputDir,name+"."+l1+"."+outputFormat),mode="w",encoding="utf8")
				output2=open(os.path.join(outputDir,name+"."+l2+"."+outputFormat),mode="w",encoding="utf8")
			
				# output header
				if outputFormat=="ces":
					output1.write(cesHeader)
					output2.write(cesHeader)
				elif outputFormat=="arc":
					output1.write(arcHeader)
					output2.write(arcHeader)
					
				# output sentences
				for interval in intervals:
					(i1,j1)=interval[0]
					(i2,j2)=interval[1]
					
					for i in range(i1,i2+1):
						if outputFormat=="ces" or outputFormat=="arc":
							if inputFormat=="ces" or outputFormat=="arc":
								idSent=idSents1[i]
							else:
								idSent=str(i+1)
							output1.write("<s id=\""+idSent+"\">\n"+sents1[i]+"\n</s>\n")
						else :
							output1.write(sents1[i]+"\n")
					for j in range(j1,j2+1):
						if outputFormat=="ces" or outputFormat=="arc":
							if inputFormat=="ces" or outputFormat=="arc":
								idSent=idSents2[j]
							else:
								idSent=str(j+1)
							output2.write("<s id=\""+idSent+"\">\n"+sents2[j]+"\n</s>\n")
						else :
							output2.write(sents2[j]+"\n")
				
				# output footer
				if outputFormat=="ces":
					output1.write(cesFooter)
					output2.write(cesFooter)
				elif outputFormat=="arc":
					output1.write(cesFooter)
					output2.write(cesFooter)
				
				output1.close()
				output2.close()
				
	if 	verbose:
		print ("Terminated in",time.monotonic()-t0,"s.")				

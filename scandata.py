import os
import sys
import json
from random import shuffle
import random
#import Tkinter
#import tkMessageBox
import numpy as np
import math

NUM_PER_GROUP=2

if len(sys.argv)<2:
    print 'usage: '+sys.argv[0]+' directory [+:add] [-[-]:progress] [c:create split] [f:poputate info from template [group]] [s:stats]'
    exit()

directory = sys.argv[1]
progress=False
add=False
makesplit=False
saveall=False
populate=False
onlyGroup=None
tableList=False
getStats=False
if len(sys.argv)>2:
    if sys.argv[2][0]=='-' or sys.argv[2][0]=='p':
        progress=True
    elif sys.argv[2][0]=='+':
        add=True
    elif sys.argv[2][0]=='c':# or sys.argv[2][0]=='s' :
        makesplit=True
        if len(sys.argv[2])>1 and sys.argv[2][1]=='s':
            simpleDataset=True
        else:
            simpleDataset=False
    elif sys.argv[2][0]=='a':
        saveall=True
    elif sys.argv[2][0]=='s':
        getStats=True
    elif sys.argv[2][0]=='f':
        populate=True
        if len(sys.argv)>3:
            onlyGroup=sys.argv[3]
    elif sys.argv[2][0]=='t':
        tableList=True
    else:
        startHere = sys.argv[2]
        going=False
else:
    progress=True

if directory[-1]!='/':
    directory=directory+'/'
rr=directory[directory[:-1].rindex('/')+1:-1]
imageGroups={}
groupNames=[]
for root, dirs, files in os.walk(directory):
    #print 'root: '+root
    if root[-1]=='/':
        root=root[:-1]
    groupName = root[root.rindex('/')+1:]
    if rr==groupName:
        continue
    imageGroups[groupName]=sorted(files)
    groupNames.append(groupName)

if progress:
    numTemplateDone=0
    temped=[]
    numDoneTotal=0
    numTotal=0
    numTimed=0
    timed=[]
    timedAlign=[]
    timedIsTemp=[]
    timeTotal=0
    numTempTimed=0
    timeTemp=0
    if len(sys.argv)>2 and len(sys.argv[2])>1:
        doTime=True
    else:
        doTime=False
    for groupName in sorted(groupNames):
        files = imageGroups[groupName]
        imagesInGroup=0
        numDoneG=0
        templateImage=None
        timesByImage={}
        for f in files:
            if 'lock' not in f:
                if f[-4:]=='.jpg' or f[-5:]=='.jpeg' or f[-4:]=='.png':
                    imagesInGroup+=1
                elif 'templa' in f and f[-5:]=='.json':
                    numTemplateDone+=1
                    if doTime:
                        with open(os.path.join(directory,groupName,f)) as annFile:
                            read = json.loads(annFile.read())
                            if 'labelTime' in read and read['labelTime'] is not None:
                                numTempTimed+=1
                                temped.append(read['labelTime'])
                                timeTemp+=read['labelTime']
                            assert templateImage is None
                            templateImage = read['imageFilename']
                elif f[-5:]=='.json':
                    numDoneG+=1
                    if doTime:
                        with open(os.path.join(directory,groupName,f)) as annFile:
                            read = json.loads(annFile.read())
                            if 'labelTime' in read and read['labelTime'] is not None:
                                numTimed+=1
                                timeTotal+=read['labelTime']
                                timed.append(read['labelTime'])
                                timesByImage[read['imageFilename']]=read['labelTime']
        for image,time in timesByImage.iteritems():
            if image!=templateImage:
                timedAlign.append(time)
            else:
                timedIsTemp.append(time)
        numDoneTotal += min(numDoneG,NUM_PER_GROUP)
        numTotal += min(imagesInGroup,NUM_PER_GROUP)
    print('Templates: {}/{}  {}'.format(numTemplateDone,len(groupNames),float(numTemplateDone)/len(groupNames)))
    print('Images:    {}/{}  {}'.format(numDoneTotal,numTotal,float(numDoneTotal)/numTotal))
    if doTime:
        timeTotal/=numTimed
        timeTemp/=numTempTimed
        print (' Templates take {} secs, or {} minutes   ({} samples)'.format(timeTemp,timeTemp/60,numTempTimed))
        med = np.median(temped)
        print (' Templates(Med) take {} secs, or {} minutes   ({} samples)'.format(med,med/60,numTempTimed))
        print ('Alignment(Mean) takes {} secs, or {} minutes   ({} samples)'.format(timeTotal,timeTotal/60,numTimed))
        stddev = np.std(timed)
        print ('   std dev {} secs, or {} minutes'.format(stddev,stddev/60))
        med = np.median(timed)
        print ('Alignment(Med) takes {} secs, or {} minutes   ({} samples)'.format(med,med/60,numTimed))

        print ('\nThresholding long times...')
        thresh = stddev*2 + timeTotal
        new_time=[t for t in timed if t<thresh and t>0]
        new_temped=[t for t in temped if t<thresh and t>0]
        new_timeA=[t for t in timedAlign if t<thresh and t>0]
        new_timeT=[t for t in timedIsTemp if t<thresh and t>0]

        mean = np.mean(new_temped)
        print ('Templating(Mean) takes {} secs, or {} minutes   ({} samples)'.format(mean,mean/60,len(new_temped)))
        stddev = np.std(new_temped)
        print ('   std dev {} secs, or {} minutes'.format(stddev,stddev/60))

        mean = np.mean(new_time)
        print ('Alignment(Mean) takes {} secs, or {} minutes   ({} samples)'.format(mean,mean/60,len(new_time)))
        stddev = np.std(new_time)
        print ('   std dev {} secs, or {} minutes'.format(stddev,stddev/60))

        
        mean = np.mean(new_timeA)
        print ('Alignment not temp(Mean) takes {} secs, or {} minutes   ({} samples)'.format(mean,mean/60,len(new_timeA)))
        stddev = np.std(new_timeA)
        print ('   std dev {} secs, or {} minutes'.format(stddev,stddev/60))

        mean = np.mean(new_timeT)
        print ('Alignment is temp(Mean) takes {} secs, or {} minutes   ({} samples)'.format(mean,mean/60,len(new_timeT)))
        stddev = np.std(new_timeT)
        print ('   std dev {} secs, or {} minutes'.format(stddev,stddev/60))

    
if add:
    import matplotlib.image as mpimg
    count=0
    for groupName in sorted(groupNames):
        files = imageGroups[groupName]
        for f in files:
            if f[-5:]=='.json' and 'template' not in f:
                #print('{} / {}'.format(groupName,f))
                with open(os.path.join(directory,groupName,f)) as annFile:
                    read = json.loads(annFile.read())
                if 'height' not in read or 'width' not in read:
                    image = mpimg.imread(os.path.join(directory,groupName,f[:-5]+'.jpg'))
                    read['height']=image.shape[0]
                    read['width']=image.shape[1]
                    with open(os.path.join(directory,groupName,f),'w') as annFile:
                        annFile.write(json.dumps(read))
                        count+=1
    print 'added to '+str(count)+' jsons'

if populate:
    count=0
    for groupName in sorted(groupNames):
        if onlyGroup is not None and groupName!=onlyGroup:
            continue
        files = imageGroups[groupName]
        tempHorz=None
        for f in files:
            if 'template' in f and f[-5:]=='.json':
                with open(os.path.join(directory,groupName,f)) as tempf:
                    read = json.loads(tempf.read())
                    if 'horzLinks' in read:
                        tempHorz=read['horzLinks']
                break
        if tempHorz is not None:
            for f in files:
                if f[-5:]=='.json' and 'template' not in f:
                    with open(os.path.join(directory,groupName,f)) as annFile:
                        read = json.loads(annFile.read())
                    if 'horzLinks' not in read or len(read['horzLinks'])==0:
                        allIds = set()
                        #for bb in read['textBBs']:
                        #    addIds.add(bb['id'])
                        #for bb in read['fieldBBs']:
                        #    addIds.add(bb['id'])
                        read['horzLinks']=tempHorz
                        with open(os.path.join(directory,groupName,f),'w') as annFile:
                            annFile.write(json.dumps(read))
                            count+=1
    print 'added to '+str(count)+' jsons'


if tableList:
    groupImages={}#defaultdict(list)
    groupTablePresence={}
    sumCountField =0
    sumCountText =0
    count=0
    tableGroups=[]
    circleGroups=[]
    for groupName in sorted(groupNames):
        files = imageGroups[groupName]
        imageFiles=[]
        tempFound=False
        hasTable=False
        circleFound=False
        for f in files:
            if 'lock' not in f:
                if f[-4:]=='.jpg' or f[-5:]=='.jpeg' or f[-4:]=='.png':
                    imageFiles.append(f)
                elif 'template' in f and f[-5:]=='.json':
                    tempFound=True
                    validTemp=False
                    with open(os.path.join(directory,groupName,f)) as annFile:
                        read = json.loads(annFile.read())
                    for bb in read['fieldBBs']:
                        if bb['type']=='fieldCol' or bb['type']=='fieldRow':
                            hasTable=True
                            if validTemp:
                                break
                        if bb['type']!='fieldCol' and bb['type']!='fieldRow':
                            validTemp=True
                            if hasTable:
                                break
                        if bb['type']=='fieldCircle':
                            circleFound=True
                #elif f[-5:]=='.json' and 'temp' not in f:

        if tempFound and validTemp and hasTable:
            tableGroups.append(groupName)
            #groupImages[groupName]=imageFiles
            #groupTablePresence[groupName]=hasTable
        if tempFound and circleFound:
            circleGroups.append(groupName)
    print('Tables: {}'.format(tableGroups))
    print('Circles: {}'.format(circleGroups))
if getStats:
    groupImages={}#defaultdict(list)
    sumCountField =0
    sumCountText =0
    maxBoxes=0
    count=0
    widths=[]
    heights=[]
    ratios=[]
    rots=[]
    widths_norot=[]
    heights_norot=[]
    ratios_norot=[]
    page_heights=[]
    page_widths=[]
    page_areas=[]
    for groupName in sorted(groupNames):
        if groupName=='121':
            continue
        files = imageGroups[groupName]
        imageFiles=[]
        for f in files:
            if 'lock' not in f:
                if 'template' not in f and f[-5:]=='.json':
                    with open(os.path.join(directory,groupName,f)) as annFile:
                        read = json.loads(annFile.read())
                    sumCountField += len(read['fieldBBs'])
                    sumCountText += len(read['textBBs'])
                    count+=1
                    maxBoxes = max(maxBoxes,len(read['fieldBBs'])+len(read['textBBs']))
                    page_heights.append(read['height'])
                    page_widths.append(read['width'])
                    page_areas.append(read['height']*read['width'])
                    for bb in read['fieldBBs']+read['textBBs']:
                        if bb['type']=='fieldRow' or bb['type']=='fieldCol' or bb['type']=='fieldRegion' or bb['type']=='textRegion' or bb['type']=='graphic':
                            continue
                        tlX = bb['poly_points'][0][0]
                        tlY = bb['poly_points'][0][1]
                        trX = bb['poly_points'][1][0]
                        trY = bb['poly_points'][1][1]
                        brX = bb['poly_points'][2][0]
                        brY = bb['poly_points'][2][1]
                        blX = bb['poly_points'][3][0]
                        blY = bb['poly_points'][3][1]
                        lX = (tlX+blX)/2.0
                        lY = (tlY+blY)/2.0
                        rX = (trX+brX)/2.0
                        rY = (trY+brY)/2.0
                        height =  math.sqrt( ((blX+brX)/2.0 - (tlX+trX)/2.0)**2 + ((blY+brY)/2.0 - (tlY+trY)/2.0)**2 )
                        if height>300:
                            print '{} {}'.format(groupName,f)
                            print bb
                            continue
                        widths.append( math.sqrt( (rX - lX)**2 + (rY - lY)**2 ) )
                        heights.append( height)
                        ratios.append(widths[-1]/heights[-1])
                        rots.append(np.arctan2((rY-lY),rX-lX))

                        widths_norot.append( np.maximum.reduce((tlX,blX,trX,brX))-np.minimum.reduce((tlX,blX,trX,brX)) )
                        heights_norot.append( np.maximum.reduce((tlY,blY,trY,brY))-np.minimum.reduce((tlY,blY,trY,brY)) )
                        ratios_norot.append(widths_norot[-1]/heights_norot[-1])

    print('image mean height: {}, width: {}, area: {}'.format(np.mean(page_heights),np.mean(page_widths),np.mean(page_areas)))
    print('image std height: {}, width: {}, area: {}'.format(np.std(page_heights),np.std(page_widths),np.std(page_areas)))
    print('image max height: {}, width: {}, area: {}'.format(max(page_heights),max(page_widths),max(page_areas)))
    print('image min height: {}, width: {}, area: {}'.format(min(page_heights),min(page_widths),min(page_areas)))
    print 'avg boxes: {}'.format((sumCountField+sumCountText)/float(count))
    print 'max boxes: {}'.format(maxBoxes)
    print 'With rotation'
    print 'width mean: {}, std: {}'.format(np.mean(widths),np.std(widths))
    print 'width min: {}, max: {}'.format(min(widths),max(widths))
    print 'height mean: {}, std: {}'.format(np.mean(heights),np.std(heights))
    print 'height min: {}, max: {}'.format(min(heights),max(heights))
    print 'ratio mean: {}, std: {}'.format(np.mean(ratios),np.std(ratios))
    print 'rot mean: {}, std: {}'.format(np.mean(rots),np.std(rots))
    print 'No rotation'
    print 'width mean: {}, std: {}'.format(np.mean(widths_norot),np.std(widths_norot))
    print 'width min: {}, max: {}'.format(min(widths_norot),max(widths_norot))
    print 'height mean: {}, std: {}'.format(np.mean(heights_norot),np.std(heights_norot))
    print 'height min: {}, max: {}'.format(min(heights_norot),max(heights_norot))
    print 'ratio mean: {}, std: {}'.format(np.mean(ratios_norot),np.std(ratios_norot))

if makesplit:
    groupImages={}#defaultdict(list)
    groupTablePresence={}
    groupParaPresence={}
    for groupName in sorted(groupNames):
        files = imageGroups[groupName]
        imageFiles=[]
        tempFound=False
        hasTable=False
        isPara=False
        paraCount=0
        for f in files:
            if 'lock' not in f:
                if f[-4:]=='.jpg' or f[-5:]=='.jpeg' or f[-4:]=='.png':
                    imageFiles.append(f)
                elif 'template' in f and f[-5:]=='.json':
                    paraCount=0
                    tempFound=True
                    validTemp=False
                    with open(os.path.join(directory,groupName,f)) as annFile:
                        read = json.loads(annFile.read())
                    for bb in read['fieldBBs']:
                        if bb['type']=='fieldCol' or bb['type']=='fieldRow':
                            hasTable=True
                            if isPara:
                                break
                        if bb['type']=='fieldP':
                            paraCount+=1
                            if paraCount>2:
                                isPara=True
                                if hasTable:
                                    break
                    #for bb in read['textBBs']:
                    #    if bb['type']=='textP':
                    #        paraCount+=1
                    #        if paraCount>4:
                    #            isPara=True
                    #            if hasTable:
                    #                break
                #elif f[-5:]=='.json' and 'temp' not in f:

        groupImages[groupName]=imageFiles
        groupTablePresence[groupName]=hasTable
        groupParaPresence[groupName]=isPara
        print('group {}, table:{}, para:{} {}'.format(groupName,hasTable,isPara,'?? para' if paraCount>0 and not isPara else ''))

    groupsWithTable=[]
    groupsWithPara=[]
    groupsWithout=[]
    both=0
    for groupName in sorted(groupNames):
        if groupName in groupImages:
            if groupParaPresence[groupName] and  groupTablePresence[groupName]:
                both+=1
                if random.random()>0.5:
                    groupsWithTable.append(groupName)
                else:
                    groupsWithPara.append(groupName)
            elif groupParaPresence[groupName]:
                groupsWithPara.append(groupName)
            elif groupTablePresence[groupName]:
                groupsWithTable.append(groupName)
            else:
                groupsWithout.append(groupName)
            #print groupName
            #print '  {}'.format(len(groupImages[groupName]))
            #print '  {}'.format(groupTablePresence[groupName])
    print('Without: {}, table: {}, para: {}, (both:{})'.format(len(groupsWithout),len(groupsWithTable),len(groupsWithPara),both))
    shuffle(groupsWithTable)
    shuffle(groupsWithPara)
    shuffle(groupsWithout)
    splitWithTable = int(len(groupsWithTable)*0.1)
    splitWithPara = int(len(groupsWithPara)*0.1)
    splitWithout = int(len(groupsWithout)*0.1)

    ret={'train':{}, 'valid':{}, 'test':{}}
    if simpleDataset:
        for groupName in (groupsWithout[:splitWithout]):
            ret['valid'][groupName]=groupImages[groupName]
        for groupName in (groupsWithout[-splitWithout:]):
            ret['test'][groupName]=groupImages[groupName]
        for groupName in (groupsWithout[splitWithout:-splitWithout]):
            ret['train'][groupName]=groupImages[groupName]
        fileName='simple_train_valid_test_split.json'
    else:
        for groupName in (groupsWithPara[:splitWithPara]+groupsWithTable[:splitWithTable]+groupsWithout[:splitWithout]):
            ret['valid'][groupName]=groupImages[groupName]
        for groupName in (groupsWithPara[-splitWithPara:]+groupsWithTable[-splitWithTable:]+groupsWithout[-splitWithout:]):
            ret['test'][groupName]=groupImages[groupName]
        for groupName in (groupsWithPara[splitWithPara:-splitWithPara]+groupsWithTable[splitWithTable:-splitWithTable]+groupsWithout[splitWithout:-splitWithout]):
            ret['train'][groupName]=groupImages[groupName]
        fileName='train_valid_test_split.json'
    print('train: {}, valid: {}, test: {}'.format(len(ret['train']), len(ret['valid']), len(ret['test'])))
    with open(fileName, 'w') as out:
        out.write(json.dumps(ret,indent=4, sort_keys=True))

if saveall:
    with open('all.json','w') as out:
        out.write(json.dumps(imageGroups,indent=4, sort_keys=True))

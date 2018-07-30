from labeler import labelImage
from filelock import FileLock, FileLockException
import os
import sys
import json
import timeit
import grp

#groupId = grp.getgrnam("pairing").gr_gid
if len(sys.argv)<2:
    print 'usage: '+sys.argv[0]+' directory (startingGroup)'
    exit()

directory = sys.argv[1]
if len(sys.argv)>2:
    startHere = sys.argv[2]
    going=False
else:
    startHere=None
    going=True

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


for groupName in sorted(groupNames):
    files = imageGroups[groupName]
    if not going:
        if startHere==groupName:
            going=True
        else:
            continue
    template = None
    imageTemplate=None
    for f in files:
        if imageTemplate is None and f[-4:]=='.jpg':
            imageTemplate = files[0]

        if 'template' in f and f[-5:]=='.json':
            print 'found template for group '+groupName
            template = os.path.join(directory,groupName,f)

    if template is not None and startHere is None:
        continue

    nfTemplate = os.path.join(directory,groupName,'template'+groupName+'.json.nf')
    nfExists = os.path.exists(nfTemplate)

    print 'group '+groupName+', template image: '+imageTemplate                   
    outFile=os.path.join(directory,groupName,'template'+groupName+'.json')
    lock = FileLock(outFile, timeout=None)
    try:
        lock.acquire()
        texts=fields=pairs=samePairs=groups=page_corners=page_cornersActual=None
        if template is not None or nfExists:
            if template is not None:
                f=open(template)
            elif nfExists:
                f=open(nfTemplate)
            read = json.loads(f.read())
            f.close()
            texts=read['textBBs']
            fields=read['fieldBBs']
            pairs=read['pairs']
            samePairs=read['samePairs']
            #for i in len(samePairs):
            #    if samePairs[i][-1][0]=='f':
            groups=read['groups']
            imageTemplate=read['imageFilename']
            if 'page_corners' in read:
                page_corners=read['page_corners']
            if 'actualPage_corners' in read:
                page_cornersActual=read['actualPage_corners']
            if 'labelTime' in read:
                labelTime=read['labelTime']
                startTime = timeit.default_timer()
            else:
                labelTime=None
        else:
            labelTime=0
            startTime = timeit.default_timer()
        texts,fields,pairs,samePairs,groups,corners,actualCorners,complete = labelImage(os.path.join(directory,groupName,imageTemplate),texts,fields,pairs,samePairs,groups,None,page_corners,page_cornersActual)
        if labelTime is not None:
            labelTime+=timeit.default_timer()-startTime
        if len(texts)==0 and len(fields)==0:
            break
        if not complete:
            outFile+='.nf'
        with open(outFile,'w') as out:
            out.write(json.dumps({"textBBs":texts, "fieldBBs":fields, "pairs":pairs, "samePairs":samePairs, "groups":groups, "page_corners":corners, "imageFilename":imageTemplate, "labelTime": labelTime}))
        #os.chown(outFile,-1,groupId)
        lock.release()
        lock=None
        if not complete:
            exit()
        elif nfExists:
            os.remove(nfTemplate)
    except FileLockException as e:
        print 'template locked, moving to next group'
        lock=None
        continue
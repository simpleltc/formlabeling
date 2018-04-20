import sys
#import cv2
from matplotlib import pyplot as plt
import matplotlib.image as mpimg
import matplotlib.patches as patches
from matplotlib import gridspec
import numpy as np
import math
import json

#Globals
mouse_button=3
TOOL_WIDTH=240
toolH=40
colorMap = {'text':(0/255.0,0/255.0,255/255.0), 'textP':(0/255.0,150/255.0,255/255.0), 'textMinor':(100/255.0,190/255.0,205/255.0), 'textInst':(190/255.0,210/255.0,255/255.0), 'textNumber':(0/255.0,160/255.0,100/255.0), 'fieldCircle':(255/255.0,190/255.0,210/255.0), 'field':(255/255.0,0/255.0,0/255.0), 'fieldP':(255/255.0,120/255.0,0/255.0), 'fieldCheckBox':(255/255.0,220/255.0,0/255.0), 'graphic':(255/255.0,105/255.0,250/255.0)}
DRAW_COLOR=(1,0.7,1)
codeMap = {'text':0, 'textP':1, 'textMinor':2, 'textInst':3, 'textNumber':4, 'fieldCircle':5, 'field':6, 'fieldP':7, 'fieldCheckBox':8, 'graphic':9}
RcodeMap = {v: k for k, v in codeMap.iteritems()}
keyMap = {'text':'1',
          'textP':'2',
          'textMinor':'3',
          'textInst':'4',
          'textNumber':'5',
          'field':'q',
          'fieldP':'w',
          'fieldCheckBox':'e',
          'fieldCircle':'r',
          'graphic':'t',
          }
RkeyMap = {v: k for k, v in keyMap.iteritems()}
toolMap = {'text':'1:text/label', 'textP':'2:text para', 'textMinor':'3:minor label', 'textInst':'4:instructions', 'textNumber':'5:enumeration (#)', 'fieldCircle':'R:to be circled', 'field':'Q:field', 'fieldP':'W:field para', 'fieldCheckBox':'E:check-box', 'graphic':'T:graphic'}
toolYMap = {}
modes = ['text', 'textP', 'textMinor', 'textInst', 'textNumber', 'field', 'fieldP', 'fieldCheckBox', 'fieldCircle', 'graphic']


class Control:
    def __init__(self,ax_im,ax_tool,W,H,texts,fields,pairs,page_corners):
        self.ax_im=ax_im
        self.ax_tool=ax_tool
        self.down_cid = self.ax_im.figure.canvas.mpl_connect(
                            'button_press_event', self.clickerDown)
        self.up_cid = self.ax_im.figure.canvas.mpl_connect(
                            'button_release_event', self.clickerUp)
        self.move_cid = self.ax_im.figure.canvas.mpl_connect(
                            'motion_notify_event', self.clickerMove)
        self.key_cid = self.ax_im.figure.canvas.mpl_connect(
                            'key_press_event', self.doKey)
        self.mode='corners' #this indicates the 'state'
        self.textBBs={} #this holds each text box as (x1,y1,x2,y2,type_code,blank). x1,y1<x2,y2 and blank is always 0
        self.textRects={} #this holds the drawing patches
        self.textBBsCurId=0
        self.fieldBBs={} #this holds each field box as (x1,y1,x2,y2,type_code,blank). x1,y1<x2,y2 blank is 0/1
        self.fieldRects={} #this holds the drawing patches
        self.fieldBBsCurId=0
        self.pairing=[] #this holds each pairing as a tuple (textId,fieldId)
        self.pairLines={} #this holds drawing patches
        self.corners={'tl':None, 'tr':None, 'br':None, 'bl':None}
        self.corners_draw={'tl':None, 'tr':None, 'br':None, 'bl':None}
        #self.image=None
        #self.displayImage=None
        self.startX=-1 #where the user clicks down
        self.startY=-1
        self.endX=-1 #the current postion of the mouse, or where it was released
        self.endY=-1
        self.actionStack=[] #for undos
        self.undoStack=[] #for redos
        self.selectedId=-1
        self.selected='none'
        self.drawRect=None #drawing patch
        self.preTexts=texts
        self.preFields=fields
        self.preCorners=page_corners
        if pairs is not None:
            self.pairing=pairs
        self.corners_text = ax_im.text(W/2,H/2,'Mark the page corners, then press ENTER.\n(outer corners if two pages).\nIf odd position, press BACKSPACE for corner by corner query.',horizontalalignment='center',verticalalignment='center')
        self.ax_im.figure.canvas.draw()
        self.imageW=W
        self.imageH=H


    def init(self):
        self.corners_text.remove()
        for key, dot in self.corners_draw.iteritems():
            dot.remove()
        if self.preTexts is not None and self.preFields is not None:
            #compute an approximate transformation based on the template corners and the just labeled ones
            trans,res_,rank_,s_ = np.linalg.lstsq(np.array([[self.preCorners['tl'][0], self.preCorners['tl'][1], 1],
                                              [self.preCorners['tr'][0], self.preCorners['tr'][1], 1],
                                              [self.preCorners['br'][0], self.preCorners['br'][1], 1],
                                              [self.preCorners['bl'][0], self.preCorners['bl'][1], 1]]),
                                    np.array([[self.corners['tl'][0], self.corners['tl'][1], 1],
                                              [self.corners['tr'][0], self.corners['tr'][1], 1],
                                              [self.corners['br'][0], self.corners['br'][1], 1],
                                              [self.corners['bl'][0], self.corners['bl'][1], 1]]))
            trans = trans.transpose()
            #point_new = trans point_old, done with homogeneour cords

            for (startX,startY,endX,endY,para) in self.preTexts:
                old_corners = np.array([[startX,endX,endX,startX], #tl, tr, br, bl
                                        [startY,startY,endY,endY],
                                        [1,1,1,1]])
                new_points = np.matmul(trans,old_corners)
                new_points/=new_points[2,:] #bring back to standard homogeneous form
                startX = (new_points[0,0]+new_points[0,3])/2.0 #average x of new tl and bl
                startY = (new_points[1,0]+new_points[1,1])/2.0 #average y of new tl and tr
                endX = (new_points[0,1]+new_points[0,2])/2.0 #average x of new tr and br
                endY = (new_points[1,2]+new_points[1,3])/2.0 #average y of new br and bl
                self.textBBs[self.textBBsCurId] = (int(round(startX)),int(round(startY)),int(round(endX)),int(round(endY)),para,0)
                self.textBBsCurId+=1
            for (startX,startY,endX,endY,para,blank) in self.preFields:
                old_corners = np.array([[startX,endX,endX,startX], #tl, tr, br, bl
                                        [startY,startY,endY,endY],
                                        [1,1,1,1]])
                new_points = np.matmul(trans,old_corners)
                new_points/=new_points[2,:]
                startX = (new_points[0,0]+new_points[0,3])/2.0 #average x of new tl and bl
                startY = (new_points[1,0]+new_points[1,1])/2.0 #average y of new tl and tr
                endX = (new_points[0,1]+new_points[0,2])/2.0 #average x of new tr and br
                endY = (new_points[1,2]+new_points[1,3])/2.0 #average y of new br and bl
                self.fieldBBs[self.fieldBBsCurId] = (int(round(startX)),int(round(startY)),int(round(endX)),int(round(endY)),para,blank)
                self.fieldBBsCurId+=1
            #self.pairing=pairs
        self.mode='text'
        self.modeRect = patches.Rectangle((0,0),TOOL_WIDTH,toolH,linewidth=2,edgecolor=(1,0,1),facecolor='none')
        self.ax_tool.add_patch(self.modeRect)
        self.ax_tool.figure.canvas.draw()
        self.selectedRect = patches.Rectangle((0,0),1,1,linewidth=2,edgecolor=(1,0,1),facecolor='none')
        self.ax_im.add_patch(self.selectedRect)
        self.drawRect = patches.Rectangle((0,0),1,1,linewidth=2,edgecolor=(1,1,1),facecolor='none')
        self.ax_im.add_patch(self.drawRect)
        #self.ax_im.figure.canvas.draw()
        self.draw()

    def transAll(self,trans):
        for id in self.textBBs:
            startX,startY,endX,endY,para,blank = self.textBBs[id]
            old_corners = np.array([[startX,endX,endX,startX], #tl, tr, br, bl
                                    [startY,startY,endY,endY],
                                    [1,1,1,1]])
            new_points = np.matmul(trans,old_corners)
            new_points/=new_points[2,:] #bring back to standard homogeneous form
            startX = (new_points[0,0]+new_points[0,3])/2.0 #average x of new tl and bl
            startY = (new_points[1,0]+new_points[1,1])/2.0 #average y of new tl and tr
            endX = (new_points[0,1]+new_points[0,2])/2.0 #average x of new tr and br
            endY = (new_points[1,2]+new_points[1,3])/2.0 #average y of new br and bl
            self.textBBs[id] = (int(round(startX)),int(round(startY)),int(round(endX)),int(round(endY)),para,0)
        for id in self.fieldBBs:
            startX,startY,endX,endY,para,blank = self.fieldBBs[id]
            old_corners = np.array([[startX,endX,endX,startX], #tl, tr, br, bl
                                    [startY,startY,endY,endY],
                                    [1,1,1,1]])
            new_points = np.matmul(trans,old_corners)
            new_points/=new_points[2,:]
            startX = (new_points[0,0]+new_points[0,3])/2.0 #average x of new tl and bl
            startY = (new_points[1,0]+new_points[1,1])/2.0 #average y of new tl and tr
            endX = (new_points[0,1]+new_points[0,2])/2.0 #average x of new tr and br
            endY = (new_points[1,2]+new_points[1,3])/2.0 #average y of new br and bl
            self.fieldBBs[id] = (int(round(startX)),int(round(startY)),int(round(endX)),int(round(endY)),para,blank)
        self.draw()

    def clickerDown(self,event):
        #image,displayImage,mode,textBBs,fieldBBs,pairing = param
        if event.inaxes!=self.ax_im.axes or event.button!=mouse_button: return
        if self.mode!='delete' and self.mode!='corners':
            self.mode+='-d'
            self.startX=event.xdata
            self.startY=event.ydata

    def clickerUp(self,event):
        if event.button!=mouse_button: return
        x=event.xdata
        y=event.ydata
        if '-m' == self.mode[-2:]: #we dragged to make a box
            self.drawRect.set_bounds(0,0,1,1)
            self.mode=self.mode[:-2] #make state readable
            if abs((self.startX-self.endX)*(self.startY-self.endY))>10: #the box is "big enough"
                didPair=None #for storing auto-pair for undo/action stack

                #auto-pair to selected
                if 'text' in self.mode and 'field' in self.selected:
                    self.pairing.append((self.textBBsCurId,self.selectedId))
                    didPair=[(self.textBBsCurId,self.selectedId)]
                elif 'field' in self.mode and 'text' in self.selected:
                    self.pairing.append((self.selectedId,self.fieldBBsCurId))
                    didPair=[(self.selectedId,self.fieldBBsCurId)]

                code = codeMap[self.mode]
                selX=None
                selY=None
                selH=None
                selW=None
                if self.mode[:4]=='text':
                    self.textBBs[self.textBBsCurId]=(min(self.startX,self.endX),min(self.startY,self.endY),max(self.startX,self.endX),max(self.startY,self.endY),code,0)
                    self.actionStack.append(('add-text',self.textBBsCurId,min(self.startX,self.endX),min(self.startY,self.endY),max(self.startX,self.endX),max(self.startY,self.endY),code,0,didPair))
                    self.undoStack=[]
                    self.selectedId=self.textBBsCurId
                    self.selected='text'
                    #selX=self.textBBs[self.textBBsCurId][0]
                    #selY=self.textBBs[self.textBBsCurId][1]
                    #selW=self.textBBs[self.textBBsCurId][2]-self.textBBs[self.textBBsCurId][0]
                    #selH=self.textBBs[self.textBBsCurId][3]-self.textBBs[self.textBBsCurId][1]
                    #self.textRects[self.textBBsCurId] = patches.Rectangle((selX,selY),selW,selH,linewidth=2,edgecolor=colorMap[self.mode],facecolor='none')
                    #self.ax_im.add_patch(self.textRects[self.textBBsCurId])
                    self.selectedRect.set_bounds(self.startX-4,self.startY-4,self.endX-self.startX+8,self.endY-self.startY+8)
                    #self.textRects[self.textBBsCurId].figure.canvas.draw()
                    self.textBBsCurId+=1
                else: #self.mode[:5]=='field':
                    self.fieldBBs[self.fieldBBsCurId]=(min(self.startX,self.endX),min(self.startY,self.endY),max(self.startX,self.endX),max(self.startY,self.endY),code,0)
                    self.actionStack.append(('add-field',self.fieldBBsCurId,min(self.startX,self.endX),min(self.startY,self.endY),max(self.startX,self.endX),max(self.startY,self.endY),code,0,didPair))
                    self.undoStack=[]
                    self.selectedId=self.fieldBBsCurId
                    self.selected='field'
                    #selX=self.fieldBBs[self.fieldBBsCurId][0]
                    #selY=self.fieldBBs[self.fieldBBsCurId][1]
                    #selW=self.fieldBBs[self.fieldBBsCurId][2]-self.fieldBBs[self.fieldBBsCurId][0]
                    #selH=self.fieldBBs[self.fieldBBsCurId][3]-self.fieldBBs[self.fieldBBsCurId][1]
                    #self.fieldRects[self.fieldBBsCurId] = patches.Rectangle((selX,selY),selW,selH,linewidth=2,edgecolor=colorMap[self.mode],facecolor='none')
                    #self.ax_im.add_patch(self.fieldRects[self.fieldBBsCurId])
                    self.selectedRect.set_bounds(self.startX-4,self.startY-4,self.endX-self.startX+8,self.endY-self.startY+8)
                    #self.fieldRects[self.fieldBBsCurId].figure.canvas.draw()
                    self.fieldBBsCurId+=1
                self.draw()
           # draw(self)
        elif '-tl' == self.mode[-3:]:#we dragged the top-left corner to resize the selected box
            self.mode=self.mode[:-3]
            bbs = None
            if self.selected=='field':
                bbs = self.fieldBBs
                #rect = self.fieldRects[self.selectedId]
            elif self.selected=='text':
                bbs = self.textBBs
                #rect = self.textRects[self.selectedId]
            if bbs is not None:
                self.actionStack.append(('drag-'+self.selected,self.selectedId,bbs[self.selectedId][0],bbs[self.selectedId][1],bbs[self.selectedId][2],bbs[self.selectedId][3]))
                bbs[self.selectedId] = (self.endX,self.endY,bbs[self.selectedId][2],bbs[self.selectedId][3],bbs[self.selectedId][4],bbs[self.selectedId][5])
                #rect.set_bounds(bbs[self.selectedId][0],bbs[self.selectedId][1],bbs[self.selectedId][2]-bbs[self.selectedId][0],bbs[self.selectedId][3]-bbs[self.selectedId][1])
                self.selectedRect.set_bounds(bbs[self.selectedId][0]-4,bbs[self.selectedId][1]-4,bbs[self.selectedId][2]-bbs[self.selectedId][0]+8,bbs[self.selectedId][3]-bbs[self.selectedId][1]+8)
                #self.updatePairLines()
                #self.ax_im.figure.canvas.draw()
                self.draw()
        elif '-bl' == self.mode[-3:]:#we dragged the top-left corner to resize the selected box
            self.mode=self.mode[:-3]
            bbs = None
            if self.selected=='field':
                bbs = self.fieldBBs
                #rect = self.fieldRects[self.selectedId]
            elif self.selected=='text':
                bbs = self.textBBs
                #rect = self.textRects[self.selectedId]
            if bbs is not None:
                self.actionStack.append(('drag-'+self.selected,self.selectedId,bbs[self.selectedId][0],bbs[self.selectedId][1],bbs[self.selectedId][2],bbs[self.selectedId][3]))
                bbs[self.selectedId] = (self.endX,bbs[self.selectedId][1],bbs[self.selectedId][2],self.endY,bbs[self.selectedId][4],bbs[self.selectedId][5])
                #rect.set_bounds(bbs[self.selectedId][0],bbs[self.selectedId][1],bbs[self.selectedId][2]-bbs[self.selectedId][0],bbs[self.selectedId][3]-bbs[self.selectedId][1])
                self.selectedRect.set_bounds(bbs[self.selectedId][0]-4,bbs[self.selectedId][1]-4,bbs[self.selectedId][2]-bbs[self.selectedId][0]+8,bbs[self.selectedId][3]-bbs[self.selectedId][1]+8)
                #self.updatePairLines()
                #self.ax_im.figure.canvas.draw()
                self.draw()
        elif '-tr' == self.mode[-3:]:#we dragged the top-left corner to resize the selected box
            self.mode=self.mode[:-3]
            bbs = None
            if self.selected=='field':
                bbs = self.fieldBBs
                #rect = self.fieldRects[self.selectedId]
            elif self.selected=='text':
                bbs = self.textBBs
                #rect = self.textRects[self.selectedId]
            if bbs is not None:
                self.actionStack.append(('drag-'+self.selected,self.selectedId,bbs[self.selectedId][0],bbs[self.selectedId][1],bbs[self.selectedId][2],bbs[self.selectedId][3]))
                bbs[self.selectedId] = (bbs[self.selectedId][0],self.endY,self.endX,bbs[self.selectedId][3],bbs[self.selectedId][4],bbs[self.selectedId][5])
                #rect.set_bounds(bbs[self.selectedId][0],bbs[self.selectedId][1],bbs[self.selectedId][2]-bbs[self.selectedId][0],bbs[self.selectedId][3]-bbs[self.selectedId][1])
                self.selectedRect.set_bounds(bbs[self.selectedId][0]-4,bbs[self.selectedId][1]-4,bbs[self.selectedId][2]-bbs[self.selectedId][0]+8,bbs[self.selectedId][3]-bbs[self.selectedId][1]+8)
                #self.updatePairLines()
                #self.ax_im.figure.canvas.draw()
                self.draw()
        elif '-br' == self.mode[-3:]:#we dragged the top-left corner to resize the selected box
            self.mode=self.mode[:-3]
            bbs = None
            if self.selected=='field':
                bbs = self.fieldBBs
                #rect = self.fieldRects[self.selectedId]
            elif self.selected=='text':
                bbs = self.textBBs
                #rect = self.textRects[self.selectedId]
            if bbs is not None:
                self.actionStack.append(('drag-'+self.selected,self.selectedId,bbs[self.selectedId][0],bbs[self.selectedId][1],bbs[self.selectedId][2],bbs[self.selectedId][3]))
                bbs[self.selectedId] = (bbs[self.selectedId][0],bbs[self.selectedId][1],self.endX,self.endY,bbs[self.selectedId][4],bbs[self.selectedId][5])
                #rect.set_bounds(bbs[self.selectedId][0],bbs[self.selectedId][1],bbs[self.selectedId][2]-bbs[self.selectedId][0],bbs[self.selectedId][3]-bbs[self.selectedId][1])
                self.selectedRect.set_bounds(bbs[self.selectedId][0]-4,bbs[self.selectedId][1]-4,bbs[self.selectedId][2]-bbs[self.selectedId][0]+8,bbs[self.selectedId][3]-bbs[self.selectedId][1]+8)
                #self.updatePairLines()
                #self.ax_im.figure.canvas.draw()
                self.draw()
        else:
            if '-d' == self.mode[-2:]:
                self.mode=self.mode[:-2]

            if self.mode == 'corners':
                self.ax_im.set_xlim(0,self.imageW)
                self.ax_im.set_ylim(self.imageH,0)
                if x<=self.imageW/2 and y<=self.imageH/2:
                    self.corners['tl']=(x,y)
                    if self.corners_draw['tl'] is not None:
                        self.corners_draw['tl'].remove()
                        self.corners_draw['tl']=None
                    self.corners_draw['tl'], = self.ax_im.plot(x,y,'ro')
                elif x>self.imageW/2 and y<=self.imageH/2:
                    self.corners['tr']=(x,y)
                    if self.corners_draw['tr'] is not None:
                        self.corners_draw['tr'].remove()
                        self.corners_draw['tr']=None
                    self.corners_draw['tr'], = self.ax_im.plot(x,y,'ro')
                elif x>self.imageW/2 and y>self.imageH/2:
                    self.corners['br']=(x,y)
                    if self.corners_draw['br'] is not None:
                        self.corners_draw['br'].remove()
                        self.corners_draw['br']=None
                    self.corners_draw['br'], = self.ax_im.plot(x,y,'ro')
                elif x<=self.imageW/2 and y>self.imageH/2:
                    self.corners['bl']=(x,y)
                    if self.corners_draw['bl'] is not None:
                        self.corners_draw['bl'].remove()
                        self.corners_draw['bl']=None
                    self.corners_draw['bl'], = self.ax_im.plot(x,y,'ro')
                self.ax_im.figure.canvas.draw()
                return
            elif self.mode == 'corners-tl':
                self.corners['tl']=(x,y)
                if self.corners_draw['tl'] is not None:
                    self.corners_draw['tl'].remove()
                    self.corners_draw['tl']=None
                self.corners_draw['tl'], = self.ax_im.plot(x,y,'ro')
                self.corners_text.set_text('click on top right corner')
                self.mode = 'corners-tr'
                self.ax_im.figure.canvas.draw()
                return
            elif self.mode == 'corners-tr':
                self.corners['tr']=(x,y)
                if self.corners_draw['tr'] is not None:
                    self.corners_draw['tr'].remove()
                    self.corners_draw['tr']=None
                self.corners_draw['tr'], = self.ax_im.plot(x,y,'ro')
                self.corners_text.set_text('click on bottom right corner')
                self.mode = 'corners-br'
                self.ax_im.figure.canvas.draw()
                return
            elif self.mode == 'corners-br':
                self.corners['br']=(x,y)
                if self.corners_draw['br'] is not None:
                    self.corners_draw['br'].remove()
                    self.corners_draw['br']=None
                self.corners_draw['br'], = self.ax_im.plot(x,y,'ro')
                self.corners_text.set_text('click on bottom left corner')
                self.mode = 'corners-bl'
                self.ax_im.figure.canvas.draw()
                return
            elif self.mode == 'corners-bl':
                self.corners['bl']=(x,y)
                if self.corners_draw['bl'] is not None:
                    self.corners_draw['bl'].remove()
                    self.corners_draw['bl']=None
                self.corners_draw['bl'], = self.ax_im.plot(x,y,'ro')
                self.corners_text.set_text('BACKSPACE to reset. ENTER to confirm')
                self.mode = 'corners-done'
                self.ax_im.figure.canvas.draw()
                return

            if self.mode=='delete': #first check for pairing lines (we can only delete them)
                for index,(text,field) in enumerate(self.pairing):
                    #if within bounds of line and within distance from it
                    x1=(self.textBBs[text][0]+self.textBBs[text][2])/2
                    y1=(self.textBBs[text][1]+self.textBBs[text][3])/2
                    x2=(self.fieldBBs[field][0]+self.fieldBBs[field][2])/2
                    y2=(self.fieldBBs[field][1]+self.fieldBBs[field][3])/2

                    if x>=min(x1,x2) and x<=max(x1,x2) and y>=min(y1,y2) and y<=max(y1,y2) and abs((y2-y1)*x - (x2-x1)*y + x2*y1 - y2*x1)/math.sqrt(pow(y2-y1,2.0) + pow(x2-x1,2.0)) < 9.5:
                        #delete the pairing
                        self.actionStack.append(('remove-pairing',text,field))
                        self.undoStack=[]
                        #self.pairLines[index].remove()
                        #self.ax_im.figure.canvas.draw()
                        #del self.pairLines[index]
                        del self.pairing[index]
                        self.draw()
                        return
            #then bbs
            for id, (startX,startY,endX,endY,para,blank) in self.textBBs.iteritems():
                if x>=startX and x<=endX and y>=startY and y<=endY:
                    #print 'click on text b'
                    if self.mode=='delete':
                        #delete the text BB
                        pairs=[]#pairs this BB is part of
                        for i,pair in enumerate(self.pairing):
                            if id==pair[0]:
                                pairs.append(i)
                        for i in pairs:
                            #self.pairing.remove(pair)
                            del self.pairing[i]
                            #self.pairLines[i].remove()
                            #self.pairLines.remove(pair)
                            #del self.pairLines[i]
                        self.actionStack.append(('remove-text',id,startX,startY,endX,endY,para,blank,pairs))
                        self.undoStack=[]
                        #self.textRects[id].remove()
                        #del self.textRects[id]
                        del self.textBBs[id]
                        if self.selected=='text' and self.selectedId==id:
                            self.selected='none'
                            self.selectedRect.set_bounds(0,0,1,1)
                        #self.ax_im.figure.canvas.draw()

                    else:
                        #pair to prev selected?
                        if self.selected=='field' and (id,self.selectedId) not in self.pairing:
                            self.pairing.append((id,self.selectedId))
                            self.actionStack.append(('add-pairing',id,self.selectedId))
                            self.undoStack=[]
                            #x=(self.textBBs[id][2]+self.textBBs[id][0])/2
                            #y=(self.textBBs[id][3]+self.textBBs[id][1])/2
                            #xe=(self.fieldBBs[self.selectedId][2]+self.fieldBBs[self.selectedId][0])/2
                            #ye=(self.fieldBBs[self.selectedId][3]+self.fieldBBs[self.selectedId][1])/2
                            #self.pairLines[len(self.pairing)-1]=patches.Arrow(x,y,xe-x,ye-y,2,edgecolor='g',facecolor='none')
                            #self.ax_im.add_patch(self.pairLines[len(self.pairing)-1])
                            #self.ax_im.figure.canvas.draw()
                        #select the text BB
                        self.selectedId=id
                        self.selected='text'
                        self.selectedRect.set_bounds(startX-4,startY-4,endX-startX+8,endY-startY+8)
                        #self.ax_im.figure.canvas.draw()
                    self.draw()
                    return

            for id, (startX,startY,endX,endY,para,blank) in self.fieldBBs.iteritems():
                if x>=startX and x<=endX and y>=startY and y<=endY:
                    if self.mode=='delete':
                        #delete the field BB
                        pairs=[]#pairs this BB is part of
                        for i,pair in enumerate(self.pairing):
                            if id==pair[1]:
                                pairs.append(i)
                        for i in pairs:
                            del self.pairing[i]
                            #self.pairLines[i].remove()
                            #del self.pairLines[i]
                        self.actionStack.append(('remove-field',id,startX,startY,endX,endY,para,blank,pairs))
                        self.undoStack=[]
                        #self.fieldRects[id].remove()
                        #del self.fieldRects[id]
                        del self.fieldBBs[id]
                        if self.selected=='field' and self.selectedId==id:
                            self.selected='none'
                            self.selectedRect.set_bounds(0,0,1,1)
                        #self.ax_im.figure.canvas.draw()
                    else:
                        #pair to prev selected?
                        if self.selected=='text' and (self.selectedId,id) not in self.pairing:
                            self.pairing.append((self.selectedId,id))
                            self.actionStack.append(('add-pairing',self.selectedId,id))
                            self.undoStack=[]
                            #x=(self.textBBs[self.selectedId][2]+self.textBBs[self.selectedId][0])/2
                            #y=(self.textBBs[self.selectedId][3]+self.textBBs[self.selectedId][1])/2
                            #xe=(self.fieldBBs[id][2]+self.fieldBBs[id][0])/2
                            #ye=(self.fieldBBs[id][3]+self.fieldBBs[id][1])/2
                            #self.pairLines[len(self.pairing)-1]=patches.Arrow(x,y,xe-x,ye-y,2,edgecolor='g',facecolor='none')
                            #self.ax_im.add_patch(self.pairLines[len(self.pairing)-1])
                            #self.ax_im.figure.canvas.draw()
                        #select the field BB
                        self.selectedId=id
                        self.selected='field'
                        self.selectedRect.set_bounds(startX-4,startY-4,endX-startX+8,endY-startY+8)
                        #self.ax_im.figure.canvas.draw()
                    self.draw()
                    return

            if self.selected!='none':
                #print 'deselected'
                self.selected='none'

                self.selectedRect.set_bounds(0,0,1,1)
                self.ax_im.figure.canvas.draw()
                #draw(self)

    def clickerMove(self,event):           
        #moving only matters if the button is down and we've moved "enough"
        bbs = None
        if self.selected == 'field':
            bbs = self.fieldBBs
        elif self.selected == 'text':
            bbs = self.textBBs
        if '-d' == self.mode[-2:] and math.sqrt(pow(event.xdata-self.startX,2)+pow(event.ydata-self.startY,2))>2:
            if bbs is not None and self.startX>bbs[self.selectedId][0] and self.startX<bbs[self.selectedId][2] and self.startY>bbs[self.selectedId][1] and self.startY<bbs[self.selectedId][3]:
                #we are going to adjust the selected BB, but how?
                w=bbs[self.selectedId][2]-bbs[self.selectedId][0] +1
                h=bbs[self.selectedId][3]-bbs[self.selectedId][1] +1
                leftBoundary = bbs[self.selectedId][0] + 0.5*w
                rightBoundary = bbs[self.selectedId][0] + 0.5*w
                topBoundary = bbs[self.selectedId][1] + 0.5*h
                bottomBoundary = bbs[self.selectedId][1] + 0.5*h
                col=colorMap[self.mode[:-2]]
                
                if self.startX<leftBoundary and self.startY<topBoundary:#top-left corner
                    self.mode = self.mode[:-1]+'tl'
                elif self.startX<leftBoundary and self.startY>bottomBoundary:#bot-left corner
                    self.mode = self.mode[:-1]+'bl'
                elif self.startX>rightBoundary and self.startY<topBoundary:#top-right corner
                    self.mode = self.mode[:-1]+'tr'
                elif self.startX>rightBoundary and self.startY>bottomBoundary:#bot-right corner
                    self.mode = self.mode[:-1]+'br'
                #elif self.startX<leftBoundary:#left
                #    self.mode = self.mode[:-1]+'l'
                #elif self.startX>rightBoundary:#right
                #    self.mode = self.mode[:-1]+'r'
                #elif self.startY<topBoundary:#top
                #    self.mode = self.mode[:-1]+'t'
                #elif self.startY<bottomBoundary:#bot
                #    self.mode = self.mode[:-1]+'b'
                self.drawRect.set_edgecolor(col)
            elif 'none' not in self.mode and 'delete' not in self.mode:
                col=DRAW_COLOR
                if self.mode[:-2] in colorMap:
                    col=colorMap[self.mode[:-2]]
                self.mode = self.mode[:-1]+'m'
                self.drawRect.set_edgecolor(col)
                self.drawRect.set_bounds(self.startX,self.startY,event.xdata-self.startX,event.ydata-self.startY)
            else:
                self.mode = self.mode[:-2]
        if '-m' == self.mode[-2:]:
            self.endX=event.xdata
            self.endY=event.ydata
            self.drawRect.set_width(self.endX-self.startX)
            self.drawRect.set_height(self.endY-self.startY)
            self.ax_im.figure.canvas.draw()
            #draw(self)
        elif (self.mode[:6]!='corner' and
             (('-tl' == self.mode[-3:] and  event.xdata<bbs[self.selectedId][2] and event.ydata<bbs[self.selectedId][3]) or
              ('-bl' == self.mode[-3:] and  event.xdata<bbs[self.selectedId][2] and event.ydata>bbs[self.selectedId][1]) or
              ('-tr' == self.mode[-3:] and  event.xdata>bbs[self.selectedId][0] and event.ydata<bbs[self.selectedId][3]) or
              ('-br' == self.mode[-3:] and  event.xdata>bbs[self.selectedId][0] and event.ydata>bbs[self.selectedId][1]) or
              ('-l' == self.mode[-3:] and  event.xdata<bbs[self.selectedId][2]) or
              ('-r' == self.mode[-3:] and  event.xdata>bbs[self.selectedId][0]) or
              ('-t' == self.mode[-3:] and  event.ydata<bbs[self.selectedId][3]) or
              ('-b' == self.mode[-3:] and  event.ydata>bbs[self.selectedId][1]))):
            self.endX=event.xdata
            self.endY=event.ydata
            x=bbs[self.selectedId][0]
            y=bbs[self.selectedId][1]
            ex=bbs[self.selectedId][2]
            ey=bbs[self.selectedId][3]
            if '-tl' == self.mode[-3:]:
                x=self.endX
                y=self.endY
            elif '-bl' == self.mode[-3:]:
                x=self.endX
                ey=self.endY
            elif '-tr' == self.mode[-3:]:
                ex=self.endX
                y=self.endY
            elif '-br' == self.mode[-3:]:
                ex=self.endX
                ey=self.endY
            self.drawRect.set_bounds(x,y,ex-x,ey-y)
            self.ax_im.figure.canvas.draw()
            #draw(self)

    def doKey(self,event):
        if self.mode=='change':
            key = event.key
            for mode in keyMap:
                if key==keyMap[mode] and self.selected[:4]==mode[:4]:
                    if self.selected=='text':
                        self.actionStack.append(('change-text',self.selectedId,self.textBBs[self.selectedId][4]))
                        self.textBBs[self.selectedId]=(self.textBBs[self.selectedId][0],self.textBBs[self.selectedId][1],self.textBBs[self.selectedId][2],self.textBBs[self.selectedId][3],codeMap[mode],self.textBBs[self.selectedId][5])
                    elif self.selected=='field':
                        self.actionStack.append(('change-field',self.selectedId,self.fieldBBs[self.selectedId][4]))
                        self.fieldBBs[self.selectedId]=(self.fieldBBs[self.selectedId][0],self.fieldBBs[self.selectedId][1],self.fieldBBs[self.selectedId][2],self.fieldBBs[self.selectedId][3],codeMap[mode],self.textBBs[self.selectedId][5])
                    self.draw()

            self.mode=self.tmpMode
            self.modeRect.set_y(toolYMap[self.mode])
            self.ax_tool.figure.canvas.draw()
            #drawToolbar(p)
        elif self.mode[:6] == 'corner':
            if event.key=='escape': #quit
                self.textBBs={}
                self.fieldBBs={}
                self.pairing=[]
                self.corners={}
                plt.close('all')
            elif event.key=='backspace':
                self.corners['tl']=None
                if self.corners_draw['tl'] is not None:
                    self.corners_draw['tl'].remove()
                    self.corners_draw['tl']=None
                self.corners['tr']=None
                if self.corners_draw['tr'] is not None:
                    self.corners_draw['tr'].remove()
                    self.corners_draw['tr']=None
                self.corners['br']=None
                if self.corners_draw['br'] is not None:
                    self.corners_draw['br'].remove()
                    self.corners_draw['br']=None
                self.corners['bl']=None
                if self.corners_draw['bl'] is not None:
                    self.corners_draw['bl'].remove()
                    self.corners_draw['bl']=None
                self.corners_text.set_text('click on the top left corner')
                self.mode='corners-tl'
                self.ax_im.figure.canvas.draw()
            elif event.key=='enter':
                if self.corners['tl'] is not None and self.corners['tr'] is not None and self.corners['br'] is not None and self.corners['bl'] is not None:
                    self.init()
        else:
            key = event.key
            if key in RkeyMap:
                newMode = RkeyMap[key]
                if self.mode != newMode:
                    self.mode = newMode
                    self.modeRect.set_y(toolYMap[self.mode])
                    self.ax_tool.figure.canvas.draw()
                    #print newMode
                    #drawToolbar(p)
            elif key=='escape': #quit
                plt.close('all')
            elif key=='f': #delete:
                if self.mode != 'delete':
                    self.modeRect.set_y(toolYMap['delete'])
                    self.ax_tool.figure.canvas.draw()
                    self.mode='delete'
                    #drawToolbar(p)
            elif key=='a': # undo
                self.undo()
            elif key=='s': #S redo
                self.redo()
            elif key=='d': #D change
                self.change()
            elif key=='z': #Z blank
                self.flipBlank()
            elif key=='up':
                trans = np.array([[1,0,0],
                                  [0,1,-2],
                                  [0,0,1]])
                self.transAll(trans)
            elif key=='down':
                trans = np.array([[1,0,0],
                                  [0,1,2],
                                  [0,0,1]])
                self.transAll(trans)
            elif key=='left':
                trans = np.array([[1,0,-2],
                                  [0,1,0],
                                  [0,0,1]])
                self.transAll(trans)
            elif key=='right':
                trans = np.array([[1,0,2],
                                  [0,1,0],
                                  [0,0,1]])
                self.transAll(trans)
            elif key==',':
                t=0.01
                x=self.imageW/2.0
                y=self.imageH/2.0
                trans = np.array([[math.cos(t),-math.sin(t),-x*math.cos(t)+y*math.sin(t)+x],
                                  [math.sin(t),math.cos(t),-x*math.sin(t)-y*math.cos(t)+y],
                                  [0,0,1]])
                self.transAll(trans)
            elif key=='.':
                t=-0.01
                x=self.imageW/2.0
                y=self.imageH/2.0
                trans = np.array([[math.cos(t),-math.sin(t),-x*math.cos(t)+y*math.sin(t)+x],
                                  [math.sin(t),math.cos(t),-x*math.sin(t)-y*math.cos(t)+y],
                                  [0,0,1]])
                self.transAll(trans)
            elif key=='backspace':
                self.draw()

    #def updatePairLines(self):
    #    for i, pair in enumerate(self.pairing):
    #        if (self.selected=='text' and pair[0]==self.selectedId) or (self.selected=='field' and pair[1]==self.selectedId):
    #            x=(self.textBBs[pair[0]][2]+self.textBBs[pair[0]][0])/2
    #            y=(self.textBBs[pair[0]][3]+self.textBBs[pair[0]][1])/2
    #            xe=(self.fieldBBs[pair[1]][2]+self.fieldBBs[pair[1]][0])/2
    #            ye=(self.fieldBBs[pair[1]][3]+self.fieldBBs[pair[1]][1])/2
    #            #self.pairLines[i].set_x(x)
    #            #self.pairLines[i].set_y(y)
    #            #self.pairLines[i].set_dx(xe-x)
    #            #self.pairLines[i].set_dy(ye-y)
    #            self.pairLines[i].remove()
    #            self.pairLines[i]=patches.Arrow(x,y,xe-x,ye-y,2,edgecolor='g',facecolor='none')
    #            self.ax_im.add_patch(self.pairLines[i])



    def undo(self):
        if len(self.actionStack)>0:
            action = self.actionStack.pop()
            action = self.undoAction(action)

            self.undoStack.append(action)
            self.draw()

    def redo(self):
        if len(self.undoStack)>0:
            action = self.undoStack.pop()
            action = self.undoAction(action)

            self.actionStack.append(action)
            self.draw()

    def undoAction(self,action):
        if action[0] == 'add-pairing':
            #i = self.pairing.index((action[1],action[2]))
            self.pairing.remove((action[1],action[2]))
            #self.pairLines[i].remove()
            #del self.pairLines[i]
            #self.ax_im.figure.canvas.draw()
            return ('remove-pairing',action[1],action[2])
        elif action[0] == 'remove-pairing':
            self.pairing.append((action[1],action[2]))
            #self.pairLines[len(self.pairing)-1] = 
            return ('add-pairing',action[1],action[2])
        elif action[0] == 'add-text':
            label,id,startX,startY,endX,endY,para,blank,pairs = action
            del self.textBBs[id]
            if pairs is not None:
                for pair in pairs:
                    self.pairing.remove(pair)
            if self.selected=='text' and self.selectedId==id:
                self.selected='none'
            return ('remove-text',id,startX,startY,endX,endY,para,blank,pairs)
        elif action[0] == 'remove-text':
            label,id,startX,startY,endX,endY,para,blank,pairs = action
            self.textBBs[id]=(startX,startY,endX,endY,para,blank)
            if pairs is not None:
                for pair in pairs:
                    self.pairing.append(pair)
            return ('add-text',id,startX,startY,endX,endY,para,blank,pairs)
        elif action[0] == 'add-field':
            label,id,startX,startY,endX,endY,para,blank,pairs = action
            del self.fieldBBs[id]
            if pairs is not None:
                for pair in pairs:
                    self.pairing.remove(pair)
            if self.selected=='field' and self.selectedId==id:
                self.selected='none'
            return ('remove-field',id,startX,startY,endX,endY,para,blank,pairs)
        elif action[0] == 'remove-field':
            label,id,startX,startY,endX,endY,para,blank,pairs = action
            self.fieldBBs[id]=(startX,startY,endX,endY,para,blank)
            if pairs is not None:
                for pair in pairs:
                    self.pairing.append(pair)
            return ('add-field',id,startX,startY,endX,endY,para,blank,pairs)
        elif action[0] == 'drag-field':
            label,id,startX,startY,endX,endY = action
            toRet = (label,id,self.fieldBBs[id][0],self.fieldBBs[id][1],self.fieldBBs[id][2],self.fieldBBs[id][3])
            self.fieldBBs[id] = (startX,startY,endX,endY,self.fieldBBs[id][4],self.fieldBBs[id][5])
            return toRet
        elif action[0] == 'drag-text':
            label,id,startX,startY,endX,endY = action
            toRet = (label,id,self.textBBs[id][0],self.textBBs[id][1],self.textBBs[id][2],self.textBBs[id][3])
            code = self.textBBs[id][4]
            em = self.textBBs[id][5]
            self.textBBs[id] = (startX,startY,endX,endY,code,em)
            return toRet
        elif action[0] == 'change-text':
            label,id,code = action
            toRet = (label,id,self.textBBs[id][4])
            self.textBBs[id] = (self.textBBs[id][0],self.textBBs[id][1],self.textBBs[id][2],self.textBBs[id][3],code,self.textBBs[id][5])
            return toRet
        elif action[0] == 'change-field':
            label,id,code = action
            toRet = (label,id,self.fieldBBs[id][4])
            self.fieldBBs[id] = (self.fieldBBs[id][0],self.fieldBBs[id][1],self.fieldBBs[id][2],self.fieldBBs[id][3],code,self.fieldBBs[id][5])
            return toRet
        elif action[0] == 'flip-blank':#only occurs with fields
            label,id= action
            toRet = (label,id)
            newBlank = int(self.fieldBBs[id][4]!=1)
            self.fieldBBs[id] = (self.fieldBBs[id][0],self.fieldBBs[id][1],self.fieldBBs[id][2],self.fieldBBs[id][3],newBlank,self.fieldBBs[id][5])
            return toRet
        else:
            print 'Unimplemented action: '+action[0]

    def change(self):
            self.tmpMode = self.mode
            self.mode='change'
            self.modeRect.set_y(toolYMap['change'])
            self.ax_tool.figure.canvas.draw()
            #drawToolbar(p)

    def flipBlank(self):
        if self.selected=='field':
            self.actionStack.append(('flip-blank',self.selectedId))
            newBlank = int(self.fieldBBs[self.selectedId][5]!=1)
            self.fieldBBs[self.selectedId]=(self.fieldBBs[self.selectedId][0],self.fieldBBs[self.selectedId][1],self.fieldBBs[self.selectedId][2],self.fieldBBs[self.selectedId][3],self.fieldBBs[self.selectedId][4],newBlank)
            self.draw()


    def draw(self):
        self.drawRect.set_bounds(0,0,1,1)
        if self.selected=='field':
            self.selectedRect.set_bounds(self.fieldBBs[self.selectedId][0]-4,self.fieldBBs[self.selectedId][1]-4,self.fieldBBs[self.selectedId][2]-self.fieldBBs[self.selectedId][0]+8,self.fieldBBs[self.selectedId][3]-self.fieldBBs[self.selectedId][1]+8)
        elif self.selected=='text':
            self.selectedRect.set_bounds(self.textBBs[self.selectedId][0]-4,self.textBBs[self.selectedId][1]-4,self.textBBs[self.selectedId][2]-self.textBBs[self.selectedId][0]+8,self.textBBs[self.selectedId][3]-self.textBBs[self.selectedId][1]+8)
        else:
            self.selectedRect.set_bounds(0,0,1,1)
        #clear all
        #print self.textRects
        #print self.textBBs
        for id,rect in self.textRects.iteritems():
            rect.remove()
        self.textRects={}
        for id,rect in self.fieldRects.iteritems():
            rect.remove()
        self.fieldRects={}
        for id,line in self.pairLines.iteritems():
            line.remove()
        self.pairLines={}

        #self.displayImage[0:self.image.shape[0], 0:self.image.shape[1]] = self.image
        for id, (startX,startY,endX,endY,code,blank) in self.textBBs.iteritems():
            #cv2.rectangle(self.displayImage,(startX,startY),(endX,endY),colorMap[RcodeMap[code]],1)
            self.textRects[id] = patches.Rectangle((startX,startY),endX-startX,endY-startY,linewidth=2,edgecolor=colorMap[RcodeMap[code]],facecolor='none')
            self.ax_im.add_patch(self.textRects[id])

        for id, (startX,startY,endX,endY,code,blank) in self.fieldBBs.iteritems():
            #cv2.rectangle(self.displayImage,(startX,startY),(endX,endY),colorMap[RcodeMap[code]],1)
            fill = 'none'
            if blank==1:
                fill=(0.9,0.9,0.9,0.5)
            self.fieldRects[id] = patches.Rectangle((startX,startY),endX-startX,endY-startY,linewidth=2,edgecolor=colorMap[RcodeMap[code]],facecolor=fill)
            self.ax_im.add_patch(self.fieldRects[id])
            #if blank==1:
            #    w = endX-startX
            #    h = endY-startY
            #    cv2.rectangle(self.displayImage,(startX+2,startY+2),(endX-2,endY-2),(240,240,240),1)
            #    cv2.rectangle(self.displayImage,(int(startX+0.25*w),int(startY+0.25*h)),(int(endX-0.25*w),int(endY-0.25*h)),(240,240,240),1)
            #    cv2.rectangle(self.displayImage,(int(startX+0.15*w),int(startY+0.15*h)),(int(endX-0.15*w),int(endY-0.15*h)),(240,240,240),1)
            #    cv2.rectangle(self.displayImage,(int(startX+0.35*w),int(startY+0.35*h)),(int(endX-0.35*w),int(endY-0.35*h)),(240,240,240),1)

        id=0
        for text,field in self.pairing:
            x1=(self.textBBs[text][0]+self.textBBs[text][2])/2
            y1=(self.textBBs[text][1]+self.textBBs[text][3])/2
            x2=(self.fieldBBs[field][0]+self.fieldBBs[field][2])/2
            y2=(self.fieldBBs[field][1]+self.fieldBBs[field][3])/2
            #cv2.line(self.displayImage,(x1,y1),(x2,y2),(0,255,0),1)
            self.pairLines[id]=patches.Arrow(x1,y1,x2-x1,y2-y1,2,edgecolor='g',facecolor='none')
            self.ax_im.add_patch(self.pairLines[id])
            id+=1

        #if self.selected == 'text':
        #    self.selectedRect.set_bounds(self.startX-4,self.startY-4,self.endX-self.startX+8,self.endY-self.startY+8)
        #    startX,startY,endX,endY,para,blank = self.textBBs[self.selectedId]
        #    if self.mode[-3:]=='-tl':
        #        cv2.rectangle(self.displayImage,(self.endX,self.endY),(max(startX,endX),max(startY,endY)),(255,240,100),1)
        #    elif self.mode[-3:]=='-tr':
        #        cv2.rectangle(self.displayImage,(startX,self.endY),(self.endX,endY),(255,240,100),1)
        #    elif self.mode[-3:]=='-bl':
        #        cv2.rectangle(self.displayImage,(self.endX,startY),(endX,self.endY),(255,240,100),1)
        #    elif self.mode[-3:]=='-br':
        #        cv2.rectangle(self.displayImage,(startX,startY),(self.endX,self.endY),(255,240,100),1)
        #    cv2.rectangle(self.displayImage,(min(startX,endX)-2,min(startY,endY)-2),(max(startX,endX)+2,max(startY,endY)+2),(255,0,255),1)
        #elif self.selected == 'field':
        #    startX,startY,endX,endY,para,blank = self.fieldBBs[self.selectedId]
        #    if self.mode[-3:]=='-tl':
        #        cv2.rectangle(self.displayImage,(self.endX,self.endY),(max(startX,endX),max(startY,endY)),(120,255,255),1)
        #    elif self.mode[-3:]=='-tr':
        #        cv2.rectangle(self.displayImage,(startX,self.endY),(self.endX,endY),(120,255,255),1)
        #    elif self.mode[-3:]=='-bl':
        #        cv2.rectangle(self.displayImage,(self.endX,startY),(endX,self.endY),(120,255,255),1)
        #    elif self.mode[-3:]=='-br':
        #        cv2.rectangle(self.displayImage,(startX,startY),(self.endX,self.endY),(120,255,255),1)
        #    cv2.rectangle(self.displayImage,(min(startX,endX)-2,min(startY,endY)-2),(max(startX,endX)+2,max(startY,endY)+2),(255,0,255),1)

        #if self.mode[-2:]=='-m':
        #    cv2.rectangle(self.displayImage,(self.startX,self.startY),(self.endX,self.endY),colorMap[self.mode[:-2]],1)

        #cv2.imshow("labeler",self.displayImage)
        self.ax_im.figure.canvas.draw()

def drawToolbar(ax):
    #im[0:,-TOOL_WIDTH:]=(140,140,140)
    im = np.zeros(((toolH+1)*(len(modes)+5),TOOL_WIDTH,3),dtype=np.uint8)
    im[:,:,:] = 140

    y=0

    for mode in modes:
        im[y:y+toolH,TOOL_WIDTH:]=colorMap[mode]
        #if self.mode==mode:
        #    cv2.rectangle(im,(im.shape[1]TOOL_WIDTH-1,y),(im.shape[1]-1,y+toolH),(255,0,255),2)
        #cv2.putText(im,toolMap[mode],(im.shape[1]TOOL_WIDTH-3,y+toolH-3),cv2.FONT_HERSHEY_PLAIN,2.0,(40,40,40))
        ax.text(1,y+toolH-1,toolMap[mode])
        toolYMap[mode]=y
        y+=toolH+1

    #undo
    im[y:y+toolH,TOOL_WIDTH:]=(160,160,160)
    ax.text(1,y+toolH-1,'A:undo')
    y+=toolH+1

    #redo
    im[y:y+toolH,TOOL_WIDTH:]=(190,190,190)
    ax.text(1,y+toolH-1,'S:redo')
    y+=toolH+1

    #change
    im[y:y+toolH,TOOL_WIDTH:]=(230,230,230)
    #if self.mode=='change':
    #    cv2.rectangle(im,(im.shape[1]TOOL_WIDTH-1,y),(im.shape[1]-1,y+toolH),(255,0,255),2)
    ax.text(1,y+toolH-1,'D:switch type')
    toolYMap['change']=y
    y+=toolH+1

    #delete
    im[y:y+toolH,TOOL_WIDTH:]=(250,250,250)
    #if self.mode=='delete':
    #    cv2.rectangle(im,(im.shape[1]TOOL_WIDTH-1,y),(im.shape[1]-1,y+toolH),(255,0,255),2)
    ax.text(1,y+toolH-1,'F:delete')
    toolYMap['delete']=y
    y+=toolH+1

    #blank
    im[y:y+toolH,TOOL_WIDTH:]=(30,30,30)
    #if self.mode=='blank':
    #    cv2.rectangle(im,(im.shape[1]TOOL_WIDTH-1,y),(im.shape[1]-1,y+toolH),(255,0,255),2)
    #cv2.putText(im,'Z:mark blank',(im.shape[1]TOOL_WIDTH-3,y+toolH-3),cv2.FONT_HERSHEY_PLAIN,2.0,(240,240,240))
    ax.text(1,y+toolH-1,'Z:mark blank')
    toolYMap['blank']=y
    y+=toolH+1

    return im

    #cv2.imshow("labeler",self.displayImage)
        

def labelImage(imagePath,displayH,displayW,texts,fields,pairs,page_corners):
    #p = Params()
    image = mpimg.imread(sys.argv[1])
    #if p.image is None:
    #    print 'cannot open image '+imagePath
    #    exit(1)
    #scale = min(float(displayH)/p.image.shape[0],float(displayW-TOOL_WIDTH)/p.image.shape[1])
    #p.image=cv2.resize(p.image,(0,0),None,scale,scale)
    


    #cv2.namedWindow("labeler")
    #cv2.setMouseCallback("labeler", clicker,param=p)
    #draw(p)
    #drawToolbar(p)
    #cv2.imshow('labeler',p.displayImage)

    #fig,axs = plt.subplots(1,2)
    fig = plt.figure()
    gs = gridspec.GridSpec(1, 2, width_ratios=[8, 1])
    ax_im = plt.subplot(gs[0])
    ax_im.set_axis_off()
    ax_im.imshow(image,cmap='gray')
    ax_tool = plt.subplot(gs[1])
    ax_tool.set_axis_off()
    toolImage = drawToolbar(ax_tool)
    ax_tool.imshow(toolImage)
    ax_im.figure.canvas.mpl_disconnect(fig.canvas.manager.key_press_handler_id)
    control = Control(ax_im,ax_tool,image.shape[1],image.shape[0],texts,fields,pairs,page_corners)
    #control.draw()
    plt.show()


    idToIdxText={}
    textBBs=[]
    for id, (startX,startY,endX,endY,para,blank) in control.textBBs.iteritems():
        idToIdxText[id]=len(textBBs)
        textBBs.append((int(round(startX)),int(round(startY)),int(round(endX)),int(round(endY)),para))
    idToIdxField={}
    fieldBBs=[]
    for id, (startX,startY,endX,endY,para,blank) in control.fieldBBs.iteritems():
        idToIdxField[id]=len(fieldBBs)
        fieldBBs.append((int(round(startX)),int(round(startY)),int(round(endX)),int(round(endY)),para,blank))
    pairing=[]
    for text,field in control.pairing:
        pairing.append((idToIdxText[text],idToIdxField[field]))

    return textBBs, fieldBBs, pairing, control.corners

texts=None
fields=None
pairs=None
page_corners=None
if len(sys.argv)>4:
    with open(sys.argv[4]) as f:
        read = json.loads(f.read())
        texts=read['textBBs']
        fields=read['fieldBBs']
        pairs=read['pairs']
        page_corners=read['page_corners']

texts,fields,pairs,corners = labelImage(sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),texts,fields,pairs,page_corners)
outFile='test.json'
if len(texts)+len(fields)+len(corners)>0:
    with open(outFile,'w') as out:
        out.write(json.dumps({"textBBs":texts, "fieldBBs":fields, "pairs":pairs, "page_corners":corners}))
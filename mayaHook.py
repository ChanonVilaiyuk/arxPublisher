import maya.cmds as mc
import maya.mel as mm

import sys, os

from tools.utils import config
reload(config)


def getSceneName() : 
	currentScene = mc.file(q = True, sn = True)
	
	return currentScene

def warning(text) : 
	mm.eval('warning "%s\\n";' % text)


def save() : 
	result = mc.file(save = True, type = 'mayaAscii')

	return result

def saveAs(filename) : 
	mc.file(rename = filename)
	result = save()

	return result


def log(message, underline = False, trace = True, doubleLine = False) : 
	
	if underline : 
		dash = str()
		for i in range(len(message)) : 
			dash = '%s%s' % (dash, '-')

	if doubleLine : 
		underline = True
		mm.eval('print "%s\\n";' % dash)

		if trace : 
			mm.eval('trace "%s";' % dash)


	mm.eval('print "%s\\n";' % message)

	if trace : 
		mm.eval('trace "%s";' % message)

	
	if underline : 
		mm.eval('print "%s\\n";' % dash)

		if trace : 
			mm.eval('trace "%s";' % dash)


def logList(messages) : 
	for each in messages : 
		mm.eval(r'print "%s\n";' % str(each).replace('\n', '\\n'))
		mm.eval(r'trace "%s";' % str(each).replace('\n', '\\n'))


def logError(message) : 
	mm.eval('error "%s\\n";' % message)


def captureScreen(dst, format, st, sequencer, w, h) : 
	mm.eval('setAttr "defaultRenderGlobals.imageFormat" 8;')
	outputFile = dst.split('.')[0]
	extension = dst.split('.')[-1]

	start = st
	end = start

	result = mc.playblast( format= 'iff' ,
							filename= outputFile,
							st=start ,
							et=end ,
							forceOverwrite=True ,
							sequenceTime=sequencer ,
							clearCache=1 ,
							viewer= 0 ,
							showOrnaments=1 ,
							fp=4 ,
							widthHeight= [w,h] ,
							percent=100 ,
							compression= format ,
							offScreen=True ,
							quality=70
							)


	if result : 
		padding = '%04d' % start 
		output = result.replace('####', padding)
		if os.path.exists(dst) : 
			os.remove(dst)
		os.rename(output, dst)

		return dst


def convertPath(inputPath) :
	try :  
		return inputPath.replace('\\', '/')

	except : 
		return inputPath
import maya.cmds as mc
import sys
sys.path.append('U:/extensions/studioTools/python')

def run() : 
	if mc.window('arxPublishWindow', exists = True) : 
	    mc.deleteUI('arxPublishWindow')
	    
	from arxPublisher import app2 as app
	reload(app)

	myApp = app.MyForm(app.getMayaWindow())
	myApp.show()

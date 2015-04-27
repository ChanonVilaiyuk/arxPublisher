# v.1.0.2
# fix overwritten publish file

# v.1.0.3
# fix increment version

# v.1.0.4
# add Shot/Sequence playblast

# v.1.0.6
# add status
# add progress bar

# v.1.0.7
# add layout task
# publish all shots to cam_pose task and versions
# remove status change for the task

#Import python modules
import sys, os, re, shutil, random
import subprocess
import getpass
from datetime import datetime
import time

# from PyQt4 import QtCore
# from PyQt4 import QtGui
# import sip
# from PyQt4.QtCore import *
# from PyQt4.QtGui import *


#Import GUI
from PySide import QtCore
from PySide import QtGui

from shiboken import wrapInstance


#Import maya commands
import maya.cmds as mc
import maya.mel as mm
from functools import partial

# import ui
from arxPublisher import ui as ui
from arxPublisher import mayaHook as hook
from tools.utils import incrementFile, fileUtils
reload(ui)
reload(hook)
reload(incrementFile)
reload(fileUtils)

from tools.utils import config
reload(config)

from sgUtils import sgUtils
reload(sgUtils)


moduleDir = sys.modules[__name__].__file__


# If inside Maya open Maya GUI
def getMayaWindow():
	ptr = mui.MQtUtil.mainWindow()
	return wrapInstance(long(ptr), QtGui.QWidget)
	# return sip.wrapinstance(long(ptr), QObject)

import maya.OpenMayaUI as mui
getMayaWindow()


class MyForm(QtGui.QMainWindow):

	def __init__(self, parent=None):
		self.count = 0
		#Setup Window
		super(MyForm, self).__init__(parent)
		# QtGui.QWidget.__init__(self, parent)
		self.ui = ui.Ui_arxPublishWindow()
		self.ui.setupUi(self)

		# custom variable
		self.configPath = hook.convertPath('%s/config.txt' % os.path.split(moduleDir)[0])
		self.publishDir = 'publish'
		self.workDir = 'work'
		self.moduleDir = moduleDir

		# icon variable 
		self.iconPath = hook.convertPath('%s/%s' % (os.path.split(self.moduleDir)[0], 'icons'))
		self.defaultIcon = hook.convertPath('%s/%s' % (self.iconPath, 'noPreview.png'))
		self.okIcon = hook.convertPath('%s/%s' % (self.iconPath, 'ok_icon.png'))
		self.xIcon = hook.convertPath('%s/%s' % (self.iconPath, 'x_icon.png'))
		self.naIcon = hook.convertPath('%s/%s' % (self.iconPath, 'na_icon.png'))
		self.snapshotDir = 'snapShots'

		# config variable
		self.configData = dict()

		# status variable
		self.statusColor = [0, 0, 160]
		self.statusGreen = [0, 0, 0]
		self.statusRed = [20, 20, 20]
		self.progress = int()
		self.progressIncrement = random.randrange(12, 16, 1)


		# set window title
		self.windowTitle = 'Arxanima Asset Publish v.1.0.6'
		self.setWindowTitle(self.windowTitle)
		self.ui.progressBar.setVisible(False)
		
		# start up function
		self.initFunction() 
		self.initConnection()

		# set logo on window
		self.setLogo()
		self.setApplicationLogo()


	def initFunction(self) : 
		# get configuration -> reading from config.txt. If config not found or not enough data, stop working.

		# welcome text
		hook.log('Launch %s' % self.windowTitle, True, False)

		rootPath = self.getConfigRootPath()

		if rootPath : 
			self.info = self.getSceneInfo(rootPath)

			if self.info : 
				self.setupUI()

			else : 
				hook.warning('Not in a correct workspace!')
				self.publishButton(False)

		else : 
			hook.warning('Not in a correct workspace!')
			self.publishButton(False)


	def initConnection(self) : 
		# setup signal for each pushButton
		self.ui.publish_pushButton.clicked.connect(self.doPublish)
		self.ui.snapViewport_pushButton.clicked.connect(self.doSnapScreen)
		self.ui.shotgun_checkBox.stateChanged.connect(self.commentBoxUI)
		self.ui.publish_radioButton.toggled.connect(self.setWorkMode)


	# ========================================================================================

		
	'''
	Configuration part
	find root path from self.configPath file

	'''

	def getConfigRootPath(self, root = 'root') : 

		# get root path from config.txt
		rootProject = str()
		windowRoot = str()
		mediaRoot = str()

		if os.path.exists(self.configPath) : 

			# reading from config.txt 
			configData = config.readSetting(self.configPath)

			if 'rootProject' in configData.keys() : 
				rootProject = configData['rootProject']

			if 'root' in configData.keys() : 
				windowRoot = eval(configData['root'])['windowRoot']

			if 'mediaRoot' in configData.keys() : 
				mediaRoot = eval(configData['mediaRoot'])['windowRoot']

			if rootProject and windowRoot and mediaRoot : 
				rootPath = '%s/%s/' % (windowRoot, rootProject)
				mediaPath = '%s/%s/' % (mediaRoot, rootProject)

				if root == 'root' : 
					return rootPath

				if root == 'media' : 
					return mediaPath

		else : 
			# return error if config not found
			hook.warning('%s not found' % self.configPath)
			self.setStatusUI('### Error %s not found' % self.configPath, 'error')

			return False


		# =========================================================================================================================


	'''
	break scene name into elements 

	'''

	def getSceneInfo(self, rootPath) : 

		print 'Reading config, Collecting scene info ...'
		self.configData = config.readSetting(self.configPath)

		# break scene name in to elements
		currentScene = hook.getSceneName()
		rootPath = self.getConfigRootPath()
		scenes = currentScene.split(rootPath)[-1]
		sceneElements = scenes.split('/')
		basename = os.path.basename(currentScene)
		errorTask = 'No Task Found'
		taskName = None
		sceneTaskName = ('_').join(basename.split('.')[0].split('_')[-2:])


		info = dict()

		if len(sceneElements) > 1 : 
			entity = sceneElements[1]

			if entity == 'assets' and len(sceneElements) == 9 : 
				projectLocal = sceneElements[0]
				workType = sceneElements[2]
				assetType = sceneElements[3]
				parent = sceneElements[4]
				variation = sceneElements[5]
				task = sceneElements[6]
				software = sceneElements[7]
				fileName = sceneElements[8]

				project = self.getProjectName(projectLocal)
				taskName = self.getTaskName(project, assetType, parent, variation, task, currentScene)

				if not taskName : 
					hook.warning('Check the task name or No task name match the scene in Shotgun')
					self.setStatusUI('### Error. Task name [%s] not found in Shotgun.' % sceneTaskName, 'error')

				else : 
					info = {
							'project': project,
							'entity': entity,
							'workType': workType,
							'assetType': assetType,
							'parent': parent,
							'variation': variation,
							'task': task,
							'software': software,
							'fileName': fileName, 
							'taskName': taskName, 
							'projectLocal': projectLocal
							}

					return info

			# if len = 9 assume that it's anim
			if entity == 'episodes' and len(sceneElements) == 9 : 
				# 'ttv/episodes/p101/work/sq010/sh020/anim/maya/ttv_p101_010_020_anim.v002.ma'
				projectLocal = sceneElements[0]
				episode = sceneElements[2]
				workType = sceneElements[3]
				sequence = sceneElements[4]
				shot = sceneElements[5]
				department = sceneElements[6]
				software = sceneElements[7]
				fileName = sceneElements[8]
				project = '%s_%s' % (projectLocal, episode)
				taskName = department
				shotProject = '%s_%s' % (projectLocal, episode)

				info = {
							'project': project,
							'entity': entity,
							'workType': workType,
							'episode': episode,
							'sequence': sequence,
							'shot': shot,
							'department': department,
							'software': software,
							'fileName': fileName, 
							'taskName': taskName, 
							'projectLocal': projectLocal
							}

				return info


			# if len = 8 assume that it's layout
			if entity == 'episodes' and len(sceneElements) == 8 : 
				# 'ttv/episodes/p101/work/sq010/layout/maya/ttv_p101_010_020_anim.v002.ma'
				projectLocal = sceneElements[0]
				episode = sceneElements[2]
				workType = sceneElements[3]
				sequence = sceneElements[4]
				department = sceneElements[5]
				software = sceneElements[6]
				fileName = sceneElements[7]
				project = '%s_%s' % (projectLocal, episode)
				taskName = department

				info = {
							'project': project,
							'entity': entity,
							'workType': workType,
							'episode': episode,
							'sequence': sequence,
							'shot': '-',
							'department': department,
							'software': software,
							'fileName': fileName, 
							'taskName': taskName, 
							'projectLocal': projectLocal
							}

				return info

		else : 
			hook.warning('Save the scene first')


	# finding task name by list all tasks in the Asset and compare to basename

	def getTaskName(self, projName, assetType, parent, variation, pipelineStep, currentScene) : 

		tasks = sgUtils.sgGetAssetTasks(projName, assetType, parent, variation, pipelineStep)
		basename = os.path.basename(currentScene)

		if tasks : 
			for each in tasks : 
				taskName = each['content']
				
				if taskName in basename : 
					return taskName


	# =====================================================================================

	'''
	Setup ui part

	'''

	def setupUI(self) : 
			
		# if this enitiy is Asset
		entity = self.info['entity']
		self.setWorkMode()
		self.setupProgressBar()

		if entity == 'assets' : 
			self.setEntityType('entity')
			self.setProject()
			self.setInfo1('Type', 'assetType')
			self.setInfo2('Parent', 'parent')
			self.setInfo3('Variation', 'variation')
			self.setTask()
			self.setPublishList()
			self.setPreview()
			self.ui.playblast_checkBox.setVisible(False)
			self.ui.upload_checkBox.setVisible(False)
			self.ui.task2_label.setVisible(False)
			self.ui.task_comboBox.setVisible(False)

		
		if entity == 'episodes' : 
			self.setEntityType('department')
			self.setProject()
			self.setInfo1('Episode', 'episode')
			self.setInfo2('Sequence', 'sequence')
			self.setInfo3('Shot', 'shot')
			self.setTask()
			self.setSGTask()
			self.setPublishList()
			self.setPreview()
			self.setPlayblastStatus()
			self.ui.upload_checkBox.setVisible(False)


	# change work environment from radioButton selection
	def setWorkMode(self) : 
		
		if self.ui.saveWork_radioButton.isChecked() :
			self.workMode = 'work' 
			self.ui.publish_pushButton.setText('Save Increment')
			self.ui.shotgun_checkBox.setEnabled(False)
			self.ui.playblast_checkBox.setEnabled(False)
			self.ui.upload_checkBox.setEnabled(False)
			listText = 'Work Files : '
			self.setPreview()

		if self.ui.publish_radioButton.isChecked() : 
			self.workMode = 'publish'
			self.ui.publish_pushButton.setText('Publish')
			self.ui.shotgun_checkBox.setEnabled(True)
			self.ui.playblast_checkBox.setEnabled(True)
			self.ui.upload_checkBox.setEnabled(True)
			listText = 'Publish Files : '
			self.setPreview()

		self.setTitleVersion(self.workMode)
		self.setPublishList()
		self.ui.display_label.setText(listText)



	def setEntityType(self, info) : 
		text = self.info[info]
		display = 'Entity : %s' % text
		self.ui.entity_label.setText(display)

	def setProject(self) : 
		text = self.info['project']
		display = 'Project : %s' % text
		self.ui.project_label.setText(display)

	def setInfo1(self, display, info) : 
		text = self.info[info]
		display = '%s : %s' % (display, text)
		self.ui.data1_label.setText(display)

	def setInfo2(self, display, info) : 
		text = self.info[info]
		display = '%s : %s' % (display, text)
		self.ui.data2_label.setText(display)

	def setInfo3(self, display, info) : 
		text = self.info[info]
		display = '%s : %s' % (display, text)
		self.ui.data3_label.setText(display)

	def setTask(self) : 
		text = self.info['taskName']
		display = 'Task : %s' % text
		self.ui.task_label.setText(display)


	def setSGTask(self) : 

		shotName = self.getShotName(self.info['department'], self.info['episode'], self.removeString(self.info['sequence']), self.removeString(self.info['shot']))
		shotTasks = sgUtils.sgGetShotTasks(self.info['project'], self.info['sequence'], shotName, self.info['department'])		

		if shotTasks : 
			self.ui.task_comboBox.clear()
			for each in shotTasks : 
				taskName = each['content']
				self.ui.task_comboBox.addItem(taskName)

		else : 
			self.setStatusUI('No Task Found', 'error')


	def setTitleVersion(self, workMode) : 

		self.workVersion = self.getWorkVersion()
		self.publishVersion = self.getPublishVersion()

		if workMode == 'work' : 
			display = 'Work : %s' % os.path.basename(self.workVersion)

		if workMode == 'publish' : 
			if os.path.exists(self.publishVersion) : 
				self.publishVersion = self.getWorkVersion()

			display = 'Publish : %s' % os.path.basename(self.publishVersion)
		
		self.ui.publish_label.setText(display)


	def setPublishList(self) : 
		if self.workMode == 'work' : 
			self.workPath = self.getWorkPath()
			crrPath = self.workPath

		if self.workMode == 'publish' : 
			self.publishPath = self.getPublishPath()
			crrPath = self.publishPath

		ext = self.configData['extension']
		snapShotExt = self.configData['snapShot']
		files = sorted(fileUtils.listFile(crrPath, ext))
		self.ui.publish_listWidget.clear()
		snapshotPath = '%s/%s' % (crrPath, self.snapshotDir)

		for eachFile in files : 
			iconFile = eachFile.replace('.%s' % ext, '.%s' % snapShotExt)
			iconPath = '%s/%s' % (snapshotPath, iconFile)

			if not os.path.exists(iconPath) : 
				iconPath = self.defaultIcon

			pathFile = '%s/%s' % (crrPath, eachFile)
			fileInfo = os.stat(pathFile)
			date = time.asctime(time.localtime(fileInfo[-1]))

			display = '%s' % eachFile
			iconSize = 90

			self.addListWidgetItem('publish_listWidget', display, iconPath, [0, 0, 0], 1, iconSize)


	def setPreview(self) : 
		self.setPreviewCmd(self.defaultIcon)


	def commentBoxUI(self) : 
		self.ui.comment_textEdit.setEnabled(True)

		if self.ui.shotgun_checkBox.isChecked() : 
			self.ui.comment_textEdit.setEnabled(True)


	def setupProgressBar(self) : 
		self.ui.progressBar.setVisible(False)
		self.ui.progressBar.setValue(0)


	# find playblast file related to sequence or shot
	def setPlayblastStatus(self) : 

		hook.log('Checking playblast ...')
		hook.log('Animation playblast', True, True, True)


		# anim department only look for 1 playblast file

		if self.info['department'] == 'anim' : 
			self.playblastVersion = self.getShotPlayblast()

			display = str()

			hook.log('Rv playblast', True, True, True)

			if self.playblastVersion['rvPlayblast'] : 
				display += 'RV Playblast available / '
				hook.log('Found %s' % self.playblastVersion['rvPlayblast'])

			else : 
				display += 'RV Playblast not found / '
				hook.log('Playblast for rv Missing')

			hook.log('Sg playblast', True, True, True)

			if self.playblastVersion['sgPlayblast'] : 
				display += 'Shotgun Playblast available, Ready to upload'
				hook.log('Found %s' % self.playblastVersion['sgPlayblast'])

			else : 
				display += 'Shotgun Playblast not found'
				hook.log('Playblast for sg Missing')

			hook.log('Summary', True, True, True)

			self.setStatusUI(display, 'success', False, False)


		# layout department will looking for shots and find available playblast for those shots

		if self.info['department'] == 'layout' : 
			self.layoutShotInfo = self.getSequencePlayblast()
			rvExists = []
			rvMissing = []
			sgExists = []
			sgMissing = []

			hook.log('Layout playblast', True, True, True)


			for each in self.layoutShotInfo : 
				if each['rvExists'] : 
					rvExists.append(each['rvPlayblast'])

				else : 
					rvMissing.append(each['rvPlayblast'])

				if each['sgExists'] : 
					sgExists.append(each['sgPlayblast'])

				else : 
					sgMissing.append(each['sgPlayblast'])


			hook.log('Rv playblast (%s files)' % len(rvExists), True, True, True)

			for each in rvExists : 
				hook.log('Found %s' % each)

			hook.log('Sg playblast (%s files)' % len(sgExists), True, True, True)

			for each in sgExists : 
				hook.log('Found %s' % each)

			hook.log('Missing Rv playblast (%s files)' % len(rvMissing), True, True, True)

			for each in rvMissing : 
				hook.log('Missing %s' % each)

			hook.log('Missing Sg playblast (%s files)' % len(sgMissing), True, True, True)

			for each in sgMissing : 
				hook.log('Missing %s' % each)

			hook.log('Summary', True, True, True)

			self.setStatusUI('%s/%s RV Playblast files available / %s/%s SG Playblast files available'  % (len(rvExists), len(self.layoutShotInfo), len(sgExists), len(self.layoutShotInfo)), 'success')



	def setLogo(self) : 
		# set company logo
		logo = self.configData['logo']
		iconPath = '%s/%s' % (self.iconPath, logo)
		self.ui.logo_label.setPixmap(QtGui.QPixmap(iconPath).scaled(200, 40, QtCore.Qt.KeepAspectRatio))


	def setApplicationLogo(self) : 
		# set company logo
		logo = self.configData['appLogo']
		iconPath = '%s/%s' % (self.iconPath, logo)
		self.ui.app_label.setPixmap(QtGui.QPixmap(iconPath).scaled(190, 28, QtCore.Qt.KeepAspectRatio))


	# ============================================================

	'''
	publish areas

	'''

	def doPublish(self) : 

		if self.workMode == 'publish' : 
			# dialog confirm to publish
			result = self.messageBox('Publish Confirm', self.getDisplayData())

			if result == QtGui.QMessageBox.Ok : 

				# check if the publish really exists
				result2 = self.checkPublish()

				# if user agree to increment version, then continue
				if result2 : 

					# log start time
					startTime = datetime.now()
					hook.log('####### Start publishing... \\n%s' % startTime, True)
					self.setProgress('==== Publish Section ====', '', True, False, '', self.statusColor)

					# save current work file
					scene = hook.save()

					self.setStatusUI('Scene save')
					self.setProgress('Scene saved', '', scene)
					self.setProgressbar(self.progressIncrement, True)

					
					# copy this version to publish dir
					result = self.makePublish(scene)

					self.setStatusUI('Publish current scene to %s' % result)
					self.setProgress('Publish', '', result)
					self.setProgressbar(self.progressIncrement, True)

					# increment work version
					workFile = self.incrementWorkVersion()

					self.setStatusUI('save current file to %s' % workFile)
					self.setProgress('Increment work file', '',  workFile)
					self.setProgressbar(self.progressIncrement, True)

					
					# connect shotgun
					self.setProgress('==== Shotgun Section ====', '', True, False, '', self.statusColor)

					self.updateShotgun()

					self.setStatusUI('==============================================')
					self.setStatusUI('Publish Complete. See Output for Details', 'success', True, False)


					# set post process
					self.setPostProcess()

					# end log
					endTime = datetime.now()
					duration = endTime - startTime
					hook.log('####### End publishing \\n%s' % endTime, True)
					hook.log('Duration %s' % duration, True)
					self.setProgress('====== Publish Complete ======', '', True, False, '', self.statusColor)
					self.setProgress('==== %s ====' % duration, '', True, False, '', self.statusColor)
					self.setProgressbar(100, True)

					# set dialog
					self.completeDialog('Publish Complete', 'Publish Complete')
					self.setProgressbar(100, False)

		if self.workMode == 'work' : 
			# increment work version
			workFile = self.incrementWorkVersion()
			self.setStatusUI('save current file to %s' % workFile)

			# set post process
			self.setPostProcess()
			self.setProgress('Save increment', '', workFile)



	def getDisplayData(self) : 		
		basename = os.path.basename(self.publishVersion)
		basenameWork = os.path.basename(self.getWorkVersion())
		status = self.configData['publishStatus']

		display = 'Publish current scene to %s\n' % basename
		display += 'Save increment version to %s\n' % basenameWork
		display += 'Update Shotgun %s status to %s\n' % (self.info['taskName'], status)
		display += '======================================\n'
		display += 'Do you want to publish?'

		return display


	def makePublish(self, scene) : 
		src = scene
		dst = self.getPublishVersion()
		result = fileUtils.copy(src, dst)

		return result


	def incrementWorkVersion(self) : 
		newVersion = self.getWorkVersion()
		result = hook.saveAs(newVersion)

		return result


	def checkPublish(self) : 
		# check if the file exists
		publishVersion = self.getPublishVersion()
		newVersion = self.getWorkVersion()

		if os.path.exists(self.getPublishVersion()) : 
			
			result = self.messageBox('File Exists', '%s exists. Increment current version to %s?' % (publishVersion, newVersion))

			if result == QtGui.QMessageBox.Ok : 
				workFile = self.incrementWorkVersion()
				self.setProgress('Publish exists, increment version', '', workFile)
				self.setProgressbar(self.progressIncrement, True)

				return True

		else : 
			return True



	def updateShotgun(self) : 

		if self.ui.shotgun_checkBox.isChecked() : 
			# flip status
			self.setStatusUI('Setting Shotgun Status')
			result = self.updateTaskStatus()

			# coordinator request to remove update status, 
			# to enable it remove the quote below 
			'''self.setProgress('Update Task status', '', result)
			'''
			# to enable update status, comment line below
			self.setProgress('Skip updating task status', '', result)
			
			self.setProgressbar(self.progressIncrement, True)


			# create version
			if result : 
				self.setStatusUI('Creating version and uploading Thumbnail ...')
				self.createShotgunVersion()

			else : 
				self.setStatusUI('No taskID, publish has stopped')
				self.setProgress('No taskID, publish has stopped', '', False)

			# create publish version


	def updateTaskStatus(self) : 
		# get taskID

		if self.info['entity'] == 'assets' : 
			self.taskID = self.getAssetTaskID()

			if self.taskID : 
				self.updateTask(self.taskID)

				return True

			else : 
				self.setStatusUI('No TaskID', 'error')

		if self.info['entity'] == 'episodes' : 
			self.taskID = self.getShotTaskID()

			if self.taskID : 
				self.updateTask(self.taskID)

				return True

			else : 
				self.setStatusUI('No TaskID', 'error')


	def getAssetTaskID(self) : 

		projName = self.info['project']
		assetType = self.info['assetType']
		parent = self.info['parent']
		variation = self.info['variation']
		taskName = self.info['taskName']
		taskID = int()

		try : 
			taskData = sgUtils.sgGetAssetTaskID(projName, assetType, parent, variation, taskName)
			self.setStatusUI('Geting taskID...')
			taskID = taskData['id']
			self.entityInfo = taskData['entity']

			return taskID

		except : 
			self.setStatusUI('#### Error #### Cannot get taskID', 'error')			
			self.setStatusUI('### Error sgUtils.sgGetAssetTaskID %s %s %s %s %s' % (projName, assetType, parent, variation, taskName), 'error')


	def getShotTaskID(self) : 

		projName = self.info['project']
		episode = self.info['episode']
		sequence = self.info['sequence']
		shot = self.removeString(self.info['shot'])
		department = self.info['department']

		# if this is a layout, task name is the same as department
		if self.info['department'] == 'layout' : 
			taskName = str(self.ui.task_comboBox.currentText())
			shotName = self.getShotName(department, episode, self.removeString(sequence), shot)

		# if this is anim task, assume task name is anim_splining
		if self.info['department'] == 'anim' : 
			# taskName = 'anim_splining'
			taskName = str(self.ui.task_comboBox.currentText())
			shotName = self.getShotName(department, episode, self.removeString(sequence), shot)

		
		taskID = int()
		publishFile = os.path.normpath(self.publishVersion)

		try : 
			self.setStatusUI('Geting taskID...')
			taskData = sgUtils.sgGetShotTaskID(projName, sequence, shotName, taskName) 
			taskID = taskData['id']
			self.entityInfo = taskData['entity']

			return taskID

		except : 
			self.setStatusUI('#### Error #### Cannot get taskID', 'error')			
			self.setStatusUI('### Error sgUtils.sgGetShotTaskID %s %s %s %s' % (projName, sequence, shotName, taskName), 'error')


	def getShotName(self, department, episode, sequence, shot) : 

		if department == 'layout' : 
			shotName = '%s_%s_%s' % (episode, sequence, department)

		if department == 'anim' : 
			shotName = '%s_%s_%s' % (episode, sequence, shot)

		return shotName



	def updateTask(self, taskID) : 
		# update task status and upload path
		publishFile = os.path.normpath(self.publishVersion)

		if taskID : 
			data = self.configData

			if 'publishStatus' in data.keys() : 
				status = data['publishStatus']

				try : 
					data = {'sg_status_list': status, 'sg_path': {'local_path': publishFile, 'name': 'MayaFile'}}

					# coordinator request to remove update status
					# to enable task status changes, remove quote below 
					'''result = sgUtils.updateTask(taskID, data)
					self.setStatusUI('Update status successful')
					'''
					self.setStatusUI('Skip updating task status')


				except : 
					self.setStatusUI('#### Error #### Update status failed', 'error')
					self.setStatusUI('%s %s' % (taskID, status))

			else : 
				hook.logError('No publishStatus in config.txt')



	def createShotgunVersion(self) : 

		projName = self.info['project']
		# taskID from update task status
		taskID = self.taskID

		# linked to entity ID -> assetID/shotID from update task status
		entityID = self.entityInfo['id']
		entityName = self.entityInfo['name']

		thumbnailPath = None

		# status of the created version, read from config.txt -> versionStatus
		status = self.configData['versionStatus']

		description = str(self.ui.comment_textEdit.toPlainText())
		ext = self.configData['extension']
		snapShotExt = self.configData['snapShot']
		mediaExt = self.configData['mediaExtension']

		# publish file
		publishPath = self.publishPath
		publishFile = self.publishVersion
		version = publishFile.split('.')[1]

		name = os.path.basename(publishFile).replace('.%s' % ext, '')
		publishPath = os.path.normpath(os.path.join(publishPath, publishFile))

		snapshotPath = os.path.join(self.publishPath, self.snapshotDir)
		previewFile = os.path.normpath(os.path.join(snapshotPath, '%s.%s' % (name, snapShotExt)))
		playblastFile = str()
		upload = False
		result = None

		if os.path.exists(previewFile) : 
			thumbnailPath = previewFile


		if self.info['entity'] == 'assets' : 
			# logging
			self.setStatusUI('Create version for Assets', '', True, True, True)
			hook.logList(['projName : %s' % projName, 'entityID : %s' % entityID, 'taskID : %s' % taskID, 
							'name : %s' % name, 'status : %s' % status, 'description : %s' % description, 
							'publishPath : %s' % hook.convertPath(publishPath), 'version : %s' % version, 
							'thumbnailPath : %s' % hook.convertPath(thumbnailPath)]
						)

			# create asset version
			result = sgUtils.sgCreateAssetVersion(projName, entityID, taskID, name, status, description, publishPath, version, thumbnailPath)

			# log result 
			hook.logList([result])
			hook.log('Create version success')

			self.setProgress('Create asset version', '', result)
			self.setProgressbar(self.progressIncrement, True)



		if self.info['entity'] == 'episodes' : 
			if self.info['department'] == 'anim' : 
				if self.ui.playblast_checkBox.isChecked() : 
					if self.playblastVersion : 
						rvPlayblast = self.playblastVersion['rvPlayblast']
						sgPlayblast = self.playblastVersion['sgPlayblast']


						# only create version if sgPlayblast available
						if sgPlayblast : 
							if self.ui.upload_checkBox.isChecked() : 
								upload = True

							self.setStatusUI('Create version for %s' % entityName, True, True, True)
							hook.logList(['projName : %s' % projName, 'entityID : %s' % entityID, 'taskID : %s' % taskID, 
										'name : %s' % name, 'status : %s' % status, 'description : %s' % description, 
										'publishPath : %s' % hook.convertPath(publishPath), 'version : %s' % version, 'thumbnailPath : %s' % hook.convertPath(thumbnailPath), 
										'rvPlayblast : %s' % hook.convertPath(rvPlayblast), 'sgPlayblast : %s' % hook.convertPath(sgPlayblast), 'upload : %s' % upload]
										)

							result = sgUtils.sgCreateShotVersion2(projName, entityID, taskID, name, status, description, publishPath, version, thumbnailPath, rvPlayblast, sgPlayblast, upload)
							hook.logList([result])
							hook.log('Create version success')
							self.setProgress('%s : Set RV Playbalst' % entityName, 'Skip : No RV playblast for %s' % entityName, rvPlayblast, True, 'na')
							self.setProgress('%s Upload SG playblast' % entityName, 'Skip : No SG Playblast for %s' % entityName, sgPlayblast, True, 'na')
							self.setProgressbar(self.progressIncrement, True)
							# self.setProgress('Create version %s' % entityName, result)

						else : 
							self.setProgress('%s : Set RV Playbalst' % entityName, 'Skip : No create version %s' % entityName, False, True, 'na')



			if self.info['department'] == 'layout' : 
				if self.ui.playblast_checkBox.isChecked() : 
					if self.layoutShotInfo : 
						incrementStep = (100 - int(self.ui.progressBar.text().replace('%', '')))/len(self.layoutShotInfo)
						for each in self.layoutShotInfo : 
							entityName = each['shotName']
							entityID = each['id']
							taskID = None
							rvPlayblast = None
							sgPlayblast = None
							upload = False
							createVersion = False


							if each['rvExists'] : 
								name = os.path.basename(each['rvPlayblast']).replace('.%s' % mediaExt, '')
								rvPlayblast = each['rvPlayblast']
								createVersion = False

							if each['sgExists'] : 
								sgPlayblast = each['sgPlayblast']
								createVersion = True

							if self.ui.upload_checkBox.isChecked() : 
								upload = True

							if createVersion : 
								self.setStatusUI('Create version for %s' % entityName, '', True, True, True)

								hook.logList(['projName : %s' % projName, 'entityID : %s' % entityID, 'taskID : %s' % taskID, 
											'name : %s' % name, 'status : %s' % status, 'description : %s' % description, 'publishPath : %s' % hook.convertPath(publishPath), 
											'version : %s' % version, 'thumbnailPath : %s' % hook.convertPath(thumbnailPath), 'rvPlayblast : %s' % rvPlayblast, 
											'sgPlayblast : %s' % hook.convertPath(sgPlayblast), 'upload : %s' % upload]
											)

								result = sgUtils.sgCreateShotVersion2(projName, entityID, taskID, name, status, description, publishPath, version, thumbnailPath, rvPlayblast, sgPlayblast, upload)

								hook.log(result)
								hook.log('Create version for %s success' % entityName)
								self.setProgress('%s : Set RV Playblast' % entityName, 'Skip : No Playblast for RV on %s' % entityName, each['rvExists'], True, 'na')
								self.setProgress('%s : Upload SG Playblast' % entityName, 'Skip : No Playblast for SG on %s' % entityName, each['sgExists'], True, 'na')
								# self.setProgress('Create version %s' % entityName, result)
								self.setProgressbar(incrementStep, True)

							else : 
								self.setProgress('Skip : No Playblast for %s' % entityName, '', False, True, 'na')
								self.setProgressbar(incrementStep, True)

		return result


	def setPostProcess(self) : 
		# refresh publish list
		self.setPublishList()

		# disabled publish button
		self.ui.publish_pushButton.setEnabled(False)


	def publishButton(self, bool) : 
		self.ui.publish_pushButton.setEnabled(bool)

	# ===============================================================================================================
	'''
	Capture Screen area

	'''

	def setPreviewCmd(self, iconPath) : 
		self.ui.preview_label.setPixmap(QtGui.QPixmap(iconPath).scaled(300, 200, QtCore.Qt.KeepAspectRatio))


	def doSnapScreen(self) : 
		result = self.snapScreen()
		self.setPreviewCmd(result)

		self.setProgress('Create %s Thumbnail' % self.workMode, '', result)


	def snapScreen(self) : 
		data = self.configData
		extension = data['extension']
		snapShotExt = data['snapShot']

		if self.workMode == 'publish' : 
			dstDir = self.getSnapshotPath('publish')
			previewFile = os.path.basename(self.publishVersion).replace('.%s' % extension, '.%s' % snapShotExt)

		if self.workMode == 'work' : 
			dstDir = self.getSnapshotPath('work')
			previewFile = os.path.basename(self.getWorkVersion()).replace('.%s' % extension, '.%s' % snapShotExt)

		dst = '%s/%s' % (dstDir, previewFile)

		if not os.path.exists(dstDir) : 
			os.makedirs(dstDir)

		format = snapShotExt
		captureFrame = mc.currentTime(q = True)
		sequencer = False
		w = 600
		h = 400
		result = hook.captureScreen(dst, format, captureFrame, sequencer, w, h)

		return result

	# ================================================================================================================================================================================================================================================

	''' 
	Get data

	'''
	# get publish path based on breaking current scene element

	def getPublishPath(self) : 
		rootPath = self.getConfigRootPath()

		if self.info['entity'] == 'assets' : 
			publishPath = os.path.join(rootPath, self.info['projectLocal'], self.info['entity'], self.publishDir, self.info['assetType'], self.info['parent'], self.info['variation'], self.info['task'], self.info['software']).replace('\\', '/')

			return publishPath

		if self.info['entity'] == 'episodes' : 
			if self.info['department'] == 'layout' : 
				publishPath = os.path.join(rootPath, self.info['projectLocal'], self.info['entity'], self.info['episode'], self.publishDir, self.info['sequence'], self.info['taskName'], self.info['software']).replace('\\', '/')

			if self.info['department'] == 'anim' : 
				publishPath = os.path.join(rootPath, self.info['projectLocal'], self.info['entity'], self.info['episode'], self.publishDir, self.info['sequence'], self.info['shot'], self.info['taskName'], self.info['software']).replace('\\', '/')

			return publishPath
		


	# get publish version by call incrementFile method

	def getPublishVersion(self) : 
		# get current scene
		currentScene = hook.getSceneName()

		# get publish path
		publishPath = self.getPublishPath()

		# read config get version string and padding
		data = self.configData
		version = data['version']
		padding = int(data['padding'])

		# get file name
		basename = self.getBasename()
		crrVersion = incrementFile.getVersionFromFile(currentScene, version, padding)
		basename = basename.replace('v000', crrVersion)

		newFile = os.path.join(publishPath, basename).replace('\\', '/')

		return newFile


	# get work version increment by call incrementFile method

	def getWorkPath(self) : 
		rootPath = self.getConfigRootPath()

		if self.info['entity'] == 'assets' : 
			workPath = os.path.join(rootPath, self.info['projectLocal'], self.info['entity'], self.workDir, self.info['assetType'], self.info['parent'], self.info['variation'], self.info['task'], self.info['software']).replace('\\', '/')

		if self.info['entity'] == 'episodes' : 
			if self.info['department'] == 'layout' : 
				# 'ttv/episodes/p101/work/sq010/sh020/anim/maya/ttv_p101_010_020_anim.v002.ma'
				workPath = os.path.join(rootPath, self.info['projectLocal'], self.info['entity'], self.info['episode'], self.workDir, self.info['sequence'], self.info['department'], self.info['software']).replace('\\', '/')

			if self.info['department'] == 'anim' : 
				workPath = os.path.join(rootPath, self.info['projectLocal'], self.info['entity'], self.info['episode'], self.workDir, self.info['sequence'], self.info['shot'], self.info['department'], self.info['software']).replace('\\', '/')

		return workPath

	def getWorkVersion(self) : 
		dir = self.getWorkPath()
		data = self.configData
		version = data['version']
		padding = int(data['padding'])
		currentScene = '%s/%s' % (dir, self.getBasename())
		newFile = incrementFile.getName(currentScene, version, padding, True)

		return newFile


	# get snapshots dir

	def getSnapshotPath(self, mode) : 
		dirInfo = {'work': self.workDir, 'publish': self.publishDir}
		rootPath = self.getConfigRootPath()

		if self.info['entity'] == 'assets' : 
			snapshotPath = os.path.join(rootPath, self.info['projectLocal'], self.info['entity'], dirInfo[mode], self.info['assetType'], self.info['parent'], self.info['variation'], self.info['task'], self.info['software'], self.snapshotDir).replace('\\', '/')

		if self.info['entity'] == 'episodes' : 
			if self.info['department'] == 'layout' : 
				snapshotPath = os.path.join(rootPath, self.info['projectLocal'], self.info['entity'], self.info['episode'], dirInfo[mode], self.info['sequence'], self.info['taskName'], self.info['software'], self.snapshotDir).replace('\\', '/')

			if self.info['department'] == 'anim' : 
				snapshotPath = os.path.join(rootPath, self.info['projectLocal'], self.info['entity'], self.info['episode'], dirInfo[mode], self.info['sequence'], self.info['shot'], self.info['taskName'], self.info['software'], self.snapshotDir).replace('\\', '/')



		return snapshotPath


	def getShotPlayblast(self) : 

		# example V:\projects\ttv\e100\sq010\sh020
		mediaRoot = self.getConfigRootPath('media')
		fileExt = '.%s' % self.configData['extension']
		mediaExt = '.%s' % self.configData['mediaExtension']

		info = {'rvPlayblast': None, 'sgPlayblast': None}

		# RV playblast path
		playblastPath = os.path.join(mediaRoot, self.info['projectLocal'], self.info['episode'], self.info['sequence'], self.info['shot'], self.info['department']).replace('\\', '/')

		# SG playblast path ex. V:/projects/ttv/e100/shotgun
		sgPlayblastPath = os.path.join(mediaRoot, self.info['projectLocal'], self.info['episode'], 'shotgun').replace('\\', '/')

		# playblast name will be the same as current work version -> ttv_e100_010_010_anim.vXXX.ma, replace .ma -> .mov
		basename = os.path.basename(self.publishVersion).replace(fileExt, mediaExt)

		# full path playblast file
		playblastFile = os.path.join(playblastPath, basename).replace('\\', '/')
		sgPlayblastFile = os.path.join(sgPlayblastPath, basename).replace('\\', '/')

		print 'Looking for RV playblast %s' % playblastFile
		print 'Looking for SG playblast %s' % sgPlayblastFile

		if os.path.exists(playblastFile) : 
			info['rvPlayblast'] = playblastFile

		if os.path.exists(sgPlayblastFile) : 
			info['sgPlayblast'] = sgPlayblastFile

		return info


	def getSequencePlayblast(self) : 

		# get file extension for .ma .mov
		mediaRoot = self.getConfigRootPath('media')
		fileExt = '.%s' % self.configData['extension']
		mediaExt = '.%s' % self.configData['mediaExtension']
		
		# get path
		playblastPath = os.path.join(mediaRoot, self.info['projectLocal'], self.info['episode'], self.info['sequence']).replace('\\', '/')

		# get sg path playblast
		sgPlayblastPath = os.path.join(mediaRoot, self.info['projectLocal'], self.info['episode'], 'shotgun').replace('\\', '/')

		
		# publish version will be ttv_e100_010_layout.vXXX.ma
		basename = os.path.basename(self.publishVersion)
		basenameEles = basename.split('_')
		layoutShotInfo = []

		# get number of shots from Shotgun Sequence ex. # {'type': 'Shot', 'id': 3567, 'name': 'e100_010_010'}
		self.sequenceInfo = sgUtils.getShotsFromSequence(self.info['project'], self.info['sequence'])

		
		for each in self.sequenceInfo : 

			# ex. e100_010_010 : the last 3 digits will be shot name
			shotName = each['name'].split('_')[-1]

			# skip layout shot
			if not 'layout' in shotName : 

				# path
				shotPath = os.path.join(playblastPath, 'sh%s' % shotName, self.info['department']).replace('\\', '/')

				# playblast file name will add shot name to the publish file
				# ttv_e100_010_XXX_layout.vXXX.mov
				playblastName = basename.replace(basenameEles[-1], ('_').join([shotName, basenameEles[-1]])).replace(fileExt, mediaExt)
				playblastFile = os.path.join(shotPath, playblastName).replace('\\', '/')

				sgPlayblastFile = os.path.join(sgPlayblastPath, playblastName).replace('\\', '/')

				exists = False
				sgExists = False

				if os.path.exists(playblastFile) : 
					exists = True

				if os.path.exists(sgPlayblastFile) : 
					sgExists = True

				# info into dict
				tempDict = {'rvPlayblast': playblastFile, 'rvExists': exists, 'sgPlayblast': sgPlayblastFile, 'sgExists': sgExists, 'shotName': shotName, 'id': each['id']}
				layoutShotInfo.append(tempDict)


		return layoutShotInfo

	# set label status

	def setStatusUI(self, message, type = '', underline = False, trace = True, doubleLine = False) : 
		self.ui.status_label.setText(message)

		if type == 'success' : 
			self.ui.status_label.setStyleSheet('color: yellow')

		if type == 'error' : 
			self.ui.status_label.setStyleSheet('color: red')

		hook.log(message, underline, trace, doubleLine)
		QtGui.QApplication.processEvents()


	def setProgress(self, textTrue, textFalse, result, icon = 1, failType = 'failed', color = []) : 

		if result : 
			iconPath = self.okIcon
			text = textTrue

			if not color : 
				color = self.statusGreen

		else : 
			if failType == 'failed' : 
				iconPath = self.xIcon

			if failType == 'na' : 
				iconPath = self.naIcon

			text = textFalse
			color = self.statusRed

			if not textFalse : 
				text = textTrue
			

		self.addListWidgetItem('status_listWidget', text, iconPath, color, icon, 14)


	
	def setProgressbar(self, value, visible) :

		previousValue = int(self.ui.progressBar.text().replace('%', ''))
		newValue = previousValue + value

		if newValue > 100 : 
			newValue = 100

		self.ui.progressBar.setValue(newValue)
		self.ui.progressBar.setVisible(visible)

		QtGui.QApplication.processEvents()


	def addListWidgetItem(self, listWidget, text, iconPath, color, addIcon = 1, size = 90) : 
 
		icon = QtGui.QIcon()
		icon.addPixmap(QtGui.QPixmap(iconPath),QtGui.QIcon.Normal,QtGui.QIcon.Off)
		cmd = 'QtGui.QListWidgetItem(self.ui.%s)' % listWidget
		item = eval(cmd)

		if addIcon : 
			item.setIcon(icon)
			cmd2 = 'self.ui.%s.setIconSize(QtCore.QSize(%s, %s))' % (listWidget, size, size)
			eval(cmd2)

		item.setText(text)
		item.setBackground(QtGui.QColor(color[0], color[1], color[2]))
		
		QtGui.QApplication.processEvents()


	def getBasename(self) : 
		# getting name elements
		data = self.configData

		if 'extension' in data.keys() : 
			extension = data['extension']

		else : 
			hook.logError('No extension found in config.txt, extension:value missing')

		project = self.info['projectLocal']

		# naming for assets 
		if self.info['entity'] == 'assets' : 
			assetType = self.info['assetType']
			parent = self.info['parent']
			variation = self.info['variation']
			taskName = self.info['taskName']
			version = 'v000'

			fileName = '%s.%s.%s' % (('_').join([project, assetType, parent, variation, taskName]), version, extension)

			return fileName

		if self.info['entity'] == 'episodes' : 
			episode = self.info['episode']
			sequence = self.removeString(self.info['sequence'])
			shot = self.removeString(self.info['shot'])
			taskName = self.info['department']
			version = 'v000'

			if self.info['department'] == 'layout' : 
				fileName = '%s.%s.%s' % (('_').join([project, episode, sequence, taskName]), version, extension)

				return fileName

			if self.info['department'] == 'anim' : 
				fileName = '%s.%s.%s' % (('_').join([project, episode, sequence, shot, taskName]), version, extension)

				return fileName



	def getProjectName(self, project) : 
		data = self.configData

		if 'projectMap' in data.keys() : 
			projectMap = eval(data['projectMap'])

			if project in projectMap.keys() : 
				mapName = projectMap[project]
				print 'map success'

				return mapName

			else : 
				print 'No projectMap setting in asset.txt'
				return project

		else : 
			print 'No projectMap in asset.txt'
			return project

	

	# ===============================================================================
	'''
	utility function

	'''

	# This function remove string from name. Example, sq010 -> 010, sh010 -> 010
	def removeString(self, inputStr) : 
		newValue = str()

		for eachStr in inputStr : 
			if eachStr.isdigit() : 
				newValue += eachStr

		return newValue


	def completeDialog(self, title, dialog) : 
		QtGui.QMessageBox.information(self, title, dialog, QtGui.QMessageBox.Ok)


	def messageBox(self, title, description) : 
		result = QtGui.QMessageBox.question(self,title,description ,QtGui.QMessageBox.Ok, QtGui.QMessageBox.Cancel)

		return result
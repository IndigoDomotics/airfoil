#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Copyright (c) 2014, Perceptive Automation, LLC. All rights reserved.
# http://www.indigodomo.com
#
# Todo:
#	• Add a "All Speakers" checkbox to the connect to/disconnect from actions

################################################################################
from appscript import *
import traceback
try:
    import indigo
except:
    pass

################################################################################
# Globals
################################################################################
airfoil = None
kAirfoilUnavailableMessage = u"Airfoil doesn't appear to be installed on your system"
kTriggerType_AirfoilAvailable = "airfoilAvailable"
kTriggerType_AirfoilUnavailable = "airfoilUnavailable"
kTriggerType_SpeakerChange = "speakerChange"
kTriggerType_SpeakerBecomesConnected = "becomesConnected"
kTriggerType_SpeakerBecomesDisconnected = "becomesDisconnected"
kTriggerType_SpeakerBecomesAvailable = "becomesAvailable"
kTriggerType_SpeakerBecomesUnavailable = "becomesUnavailable"
kTriggerType_SourceChange = "sourceChange"

########################################
def cleanName(inString=""):
    return inString.replace(" ","_")

########################################
def updateVar(name, value, folder):
    if name not in indigo.variables:
        indigo.variable.create(name, value=value, folder=folder)
    else:
        indigo.variable.updateValue(name, value)

################################################################################
class Plugin(indigo.PluginBase):
    ########################################
    # Class properties
    ########################################
    sources = dict()
    sources["application"] = list()
    sources["device"] = list()
    sources["system"] = list()
    sources["map"] = dict()
    sources["typeMap"] = dict()
    currentSource = None
    currentSourceType = "none"
    speakers = dict()
    savedSpeakerSet = dict()

    ########################################
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        super(Plugin, self).__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
        self.airfoil = None
        try:
            self.airfoil = app("Airfoil")
        except Exception, e:
            self.debugLog("Error talking to Airfoil:\n%s" % str(e))
            self.errorLog(kAirfoilUnavailableMessage)
        self.debug = pluginPrefs.get("showDebugInfo", False)
        if "isRunning" not in self.pluginPrefs:
            self.pluginPrefs["isRunning"] = False
        if "storedSpeakerSet" not in self.pluginPrefs:
            self.pluginPrefs["storedSpeakerSet"] = []
        if "storedSource" not in self.pluginPrefs:
            self.pluginPrefs["storedSource"] = []
        if "speakers" not in self.pluginPrefs:
            self.pluginPrefs["speakers"] = indigo.Dict()
        self.events = dict()
        self.events[kTriggerType_AirfoilAvailable] = dict()
        self.events[kTriggerType_AirfoilUnavailable] = dict()
        self.events[kTriggerType_SpeakerChange] = dict()
        self.events[kTriggerType_SourceChange] = dict()
        self.events[kTriggerType_SpeakerChange][kTriggerType_SpeakerBecomesConnected] = dict()
        self.events[kTriggerType_SpeakerChange][kTriggerType_SpeakerBecomesDisconnected] = dict()
        self.events[kTriggerType_SpeakerChange][kTriggerType_SpeakerBecomesAvailable] = dict()
        self.events[kTriggerType_SpeakerChange][kTriggerType_SpeakerBecomesUnavailable] = dict()
        self.throttleSkip = 10
        self.throttleCount = 10

    ########################################
    def speakerList(self, filter="", valuesDict=None, typeId="", targetId=0):
        returnList = list()
        if "speakers" in self.pluginPrefs:
            for speakerTup in self.pluginPrefs["speakers"].items():
                returnList.append((speakerTup[0],speakerTup[1][0]))
        return returnList

    ########################################
    def uiSpeakerList(self, filter="", valuesDict=None, typeId="", targetId=0):
        returnList = list()
        for speaker in self.pluginPrefs["speakers"]:
            returnList.append((speaker.split("-")[1],self.pluginPrefs["speakers"][speaker][0]))
        self.debugLog(u"Speaker List: " + unicode(returnList))
        return returnList

    ########################################
    def showSpeakerList(self):
        self.debugLog("displaying speaker list")
        printString = ""
        if (self.pluginPrefs.get("speakers", False)):
            printString = "Current Speaker List: \n"
            for speaker in self.pluginPrefs["speakers"]:
                printString += "\t Speaker: %s ID: %s\n" % (self.pluginPrefs["speakers"][speaker][0],speaker.split("-")[1])
        else:
            printString += "No speakers available"
        indigo.server.log(printString)

    ########################################
    def resetSpeakerList(self):
        self.debugLog("resetting speaker list")
        # Not sure about this yet - when you reset the speaker list should you also
        # reset the speaker variables? If you do, then all dependent actions
        # and triggers will be deleted as well.
#		if "folderId" in self.pluginPrefs:
#			speakerList = self.pluginPrefs.get("speakers",{})
#			for speaker in speakerList.itervalues():
#				cleanSpeakerName = cleanName(speaker[0])
#				if cleanSpeakerName in indigo.variables:
#					self.debugLog("deleting variable: " + cleanSpeakerName)
#					indigo.variable.delete(indigo.variables[cleanSpeakerName])
        if "speakers" in self.pluginPrefs:
            del self.pluginPrefs["speakers"]

    ########################################
    def connectToSpeaker(self, action):
        self.debugLog(u"airfoil = " + unicode(self.airfoil))
        if self.airfoil == None:
            self.errorLog(kAirfoilUnavailableMessage)
            return
        if "speaker" in action.props:
            speakerId = action.props["speaker"]
            self.debugLog(u"    connectToSpeaker id: " + speakerId)
            if speakerId in self.speakers:
                theSpeaker = self.speakers[speakerId]
                try:
                    theSpeaker.connect_to()
                except:
                    self.errorLog("Airfoil is probably not running.")
            else:
                self.errorLog(u"Speaker %s is not available" % (self.pluginPrefs["speakers"]["ID-"+speakerId][0],))
        else:
            self.errorLog(u"Speaker not selected for connect to speaker action")

    ########################################
    def disconnectFromSpeaker(self, action):
        if self.airfoil == None:
            self.errorLog(kAirfoilUnavailableMessage)
            return
        if "speaker" in action.props:
            speakerId = action.props["speaker"]
            self.debugLog(u"    disconnectFromSpeaker id: " + speakerId)
            if speakerId in self.speakers:
                theSpeaker = self.speakers[speakerId]
                try:
                    theSpeaker.disconnect_from()
                except:
                    self.errorLog("Airfoil is probably not running.")
            else:
                self.errorLog(u"Speaker %s is not available to disconnect from" % (self.pluginPrefs["speakers"]["ID-"+speakerId][0],))
        else:
            self.errorLog(u"Speaker not selected for disconnect from speaker action")

    ########################################
    def toggleSpeaker(self, action):
        if self.airfoil == None:
            self.errorLog(kAirfoilUnavailableMessage)
            return
        if "speaker" in action.props:
            speakerId = action.props["speaker"]
            self.debugLog(u"    toggleSpeaker id: " + speakerId)
            if speakerId in self.speakers:
                try:
                    theSpeaker = self.speakers[speakerId]
                    if (theSpeaker.connected.get()):
                        theSpeaker.disconnect_from()
                    else:
                        theSpeaker.connect_to()
                except:
                    self.errorLog("Airfoil is probably not running.")

            else:
                speakerKey = "ID-"+speakerId
                if speakerKey in self.pluginPrefs["speakers"]:
                    self.errorLog(u"Speaker %s is not available to toggle" % (self.pluginPrefs["speakers"][speakerKey][0],))
                else:
                    self.errorLog(u"Speaker %s is not in the speaker list - it is no longer available and the speaker list has been rebuilt" % speakerKey)
        else:
            self.errorLog(u"Speaker not selected for toggle speaker action")

    ########################################
    def connectAllSpeakers(self, action):
        self.debugLog(u"airfoil = " + unicode(self.airfoil))
        if self.airfoil == None:
            self.errorLog(kAirfoilUnavailableMessage)
            return
        self.debugLog(u"    connect all speakers")
        for speaker in self.speakers.values():
            try:
                speaker.connect_to()
            except:
                self.errorLog("Airfoil is probably not running.")


    ########################################
    def disconnectAllSpeakers(self, action):
        self.debugLog(u"airfoil = " + unicode(self.airfoil))
        if self.airfoil == None:
            self.errorLog(kAirfoilUnavailableMessage)
            return
        self.debugLog(u"    disconnect all speakers")
        for speaker in self.speakers.values():
            try:
                speaker.disconnect_from()
            except:
                self.errorLog("Airfoil is probably not running.")

    ########################################
    def saveSpeakerSet(self, action):
        if self.airfoil == None:
            self.errorLog(kAirfoilUnavailableMessage)
            return
        self.pluginPrefs["storedSpeakerSet"] = self.pluginPrefs["speakers"]

    ########################################
    def restoreSpeakerSet(self, action):
        if self.airfoil == None:
            self.errorLog(kAirfoilUnavailableMessage)
            return
        self.debugLog("restore speaker set called: ")
        for speaker in self.pluginPrefs["storedSpeakerSet"]:
            connectStr = self.pluginPrefs["storedSpeakerSet"][speaker][1]
            speakerId = speaker.split("-")[1]
            self.debugLog("    " + speakerId + " : " + connectStr)
            if speakerId in self.speakers:
                try:
                    theSpeaker = self.speakers[speakerId]
                    if connectStr == u"disconnected":
                        theSpeaker.disconnect_from()
                    else:
                        theSpeaker.connect_to()
                except:
                    self.errorLog("Airfoil is probably not running.")

    ########################################
    def saveSource(self, action):
        if self.airfoil == None:
            self.errorLog(kAirfoilUnavailableMessage)
            return
        self.pluginPrefs["storedSource"] = (self.currentSourceType,self.airfoil.get(self.currentSource.name))

    ########################################
    def restoreSource(self, action):
        if self.airfoil == None:
            self.errorLog(kAirfoilUnavailableMessage)
            return
        sourceTup = self.pluginPrefs["storedSource"]
        if (sourceTup):
            try:
                if sourceTup[0] == "application":
                    self.airfoil.current_audio_source.set(self.airfoil.application_sources[sourceTup[1]])
                elif sourceTup[0] == "device":
                    self.airfoil.current_audio_source.set(self.airfoil.device_sources[sourceTup[1]])
                else:
                    self.airfoil.current_audio_source.set(self.airfoil.system_sources[u"System Audio"])
            except:
                self.errorLog("Airfoil is probably not running.")
        else:
            self.errorLog("No source to restore - you probably haven't saved it yet")

    ########################################
    def changeAudioSource(self, action):
        if self.airfoil == None:
            self.errorLog(kAirfoilUnavailableMessage)
            return
        self.debugLog("change audio source called")
        try:
            if action.props["sourceType"] == "application":
                self.airfoil.current_audio_source.set(self.airfoil.application_sources[action.props["appSource"]])
            elif action.props["sourceType"] == "device":
                self.airfoil.current_audio_source.set(self.airfoil.device_sources[action.props["devSource"]])
            else:
                self.airfoil.current_audio_source.set(self.airfoil.system_sources[u"System Audio"])
        except:
            self.errorLog("Airfoil is probably not running.")

    ########################################
    def setVolume(self, action):
        if self.airfoil == None:
            self.errorLog(kAirfoilUnavailableMessage)
            return
        self.debugLog(u"Set Volume for speakers: " + unicode(action.props["speakerIds"]))
        if len(action.props["speakerIds"]) > 0:
            for id in action.props["speakerIds"]:
                self.debugLog("    set volume for speaker id: " + id)
                try:
                    if id in self.speakers:
                        theSpeaker = self.speakers[id]
                        try:
                            theSpeaker.volume.set(float(action.props['volume'])/100)
                        except:
                            self.errorLog("Airfoil is probably not running.")
                    else:
                        self.errorLog(u"Speaker '%s' is not available to set volume on" % (self.pluginPrefs["speakers"]["ID-"+speakerId][0],))
                except:
                    if type(id) is str:
                        self.errorLog("Speaker '%s' may not be available" % id)
                    else:
                        self.errorLog("A previously available speaker is no longer available for volume adjustment")
            return
        self.errorLog("No speakers selected for set volume action")


    ########################################
    def increaseVolume(self, action):
        if self.airfoil == None:
            self.errorLog(kAirfoilUnavailableMessage)
            return
        self.debugLog(u"Increase Volume speakers: " + unicode(action.props["speakerIds"]))
        if len(action.props["speakerIds"]) > 0:
            for id in action.props["speakerIds"]:
                try:
                    if id in self.speakers:
                        theSpeaker = self.speakers[id]
                        curVolume = theSpeaker.volume.get()
                        if type(curVolume) == list:
                            curVolume = curVolume[0]
                        curVolume = int(curVolume*100)
                    else:
                        self.errorLog(u"Speaker '%s' is not available to set volume on" % (self.pluginPrefs["speakers"]["ID-"+speakerId][0],))
                        continue
                except:
                    if type(id) is str:
                        self.errorLog("Speaker %s may not be available" % id)
                    else:
                        self.errorLog("A previously available speaker is no longer available for volume adjustment")
                    continue
                newVolume = curVolume + int(action.props['volume'])
                if newVolume > 100:
                    newVolume = 100
                self.debugLog("    increase volume for speaker id: %s from %i to % i" % (id,curVolume,newVolume))
                theSpeaker.volume.set(float(newVolume)/100)
            return
        self.errorLog("No speakers selected for set volume action")

    ########################################
    def decreaseVolume(self, action):
        if self.airfoil == None:
            self.errorLog(kAirfoilUnavailableMessage)
            return
        self.debugLog(u"Decrease Volume speakers: " + unicode(action.props["speakerIds"]))
        if len(action.props["speakerIds"]) > 0:
            for id in action.props["speakerIds"]:
                try:
                    if id in self.speakers:
                        theSpeaker = self.speakers[id]
                        curVolume = theSpeaker.volume.get()
                        if type(curVolume) == list:
                            curVolume = curVolume[0]
                        curVolume = int(curVolume*100)
                    else:
                        self.errorLog(u"Speaker '%s' is not available to set volume on" % (self.pluginPrefs["speakers"]["ID-"+speakerId][0],))
                        continue
                except:
                    if type(id) is str:
                        self.errorLog("Speaker %s may not be available" % id)
                    else:
                        self.errorLog("A previously available speaker is no longer available for volume adjustment")
                    continue
                newVolume = curVolume - int(action.props['volume'])
                if newVolume < 0:
                    newVolume = 0
                self.debugLog("    decrease volume for speaker id: %s from %i to % i" % (id,curVolume,newVolume))
                theSpeaker.volume.set(float(newVolume)/100)
            return
        self.errorLog("No speakers selected for set volume action")

    ########################################
    def triggerStartProcessing(self, trigger):
        self.debugLog(u"Start processing trigger " + unicode(trigger.id))
        triggerType = trigger.pluginTypeId
        if (triggerType == kTriggerType_AirfoilAvailable) or (triggerType == kTriggerType_AirfoilUnavailable) or (triggerType == kTriggerType_SourceChange):
            self.events[triggerType][trigger.id] = trigger
        elif (triggerType == kTriggerType_SpeakerChange):
            speakerId = trigger.pluginProps["speakerId"]
            for changeType in trigger.pluginProps["changeType"]:
                self.events[triggerType][changeType][trigger.id] = trigger
        self.debugLog(u"Start trigger processing list: " + unicode(self.events))

    ########################################
    def triggerStopProcessing(self, trigger):
        self.debugLog(u"Stop processing trigger " + unicode(trigger.id))
        triggerType = trigger.pluginTypeId
        if triggerType in self.events:
            if (triggerType == kTriggerType_AirfoilAvailable) or (triggerType == kTriggerType_AirfoilUnavailable) or (triggerType == kTriggerType_SourceChange):
                if trigger.id in self.events[triggerType]:
                    del self.events[triggerType][trigger.id]
            elif (triggerType == kTriggerType_SpeakerChange):
                speakerId = trigger.pluginProps["speakerId"]
                for changeType in trigger.pluginProps["changeType"]:
                    if trigger.id in self.events[triggerType][changeType]:
                        del self.events[triggerType][changeType][trigger.id]
        self.debugLog(u"Stop trigger processing list: " + unicode(self.events))

    ########################################
    def update(self):
        self.debugLog("update method called")
        if self.airfoil.isrunning():
            self.debugLog("update: Airfoil is running")
            # app sources
            try:
                appSources = self.airfoil.application_sources.get()
                self.debugLog(u"update: application sources: %s" % unicode(appSources))
                self.sources["map"] = dict()
                self.sources["typeMap"] = dict()
                self.sources["application"] = list()
                if appSources == None:
                    self.errorLog("The application sources list wasn't successfully retrieved from Airfoil - please check Airfoil's configuration.")
                else:
                    for source in appSources:
                        self.sources["application"].append(self.airfoil.get(source.name))
                        self.sources["map"][self.airfoil.get(source.id)] = self.airfoil.get(source.name)
                        self.sources["typeMap"][self.airfoil.get(source.id)] = "application"
                # device sources
                deviceSources = self.airfoil.device_sources.get()
                self.debugLog(u"update: device sources: %s" % unicode(deviceSources))
                self.sources["device"] = list()
                if deviceSources == None:
                    self.errorLog("The device sources list wasn't successfully retrieved from Airfoil - please check Airfoil's configuration.")
                else:
                    for source in deviceSources:
                        self.sources["device"].append(self.airfoil.get(source.name))
                        self.sources["map"][self.airfoil.get(source.id)] = self.airfoil.get(source.name)
                        self.sources["typeMap"][self.airfoil.get(source.id)] = "device"
                # system sources
                systemSources = self.airfoil.system_sources.get()
                self.debugLog(u"update: system sources: %s" % unicode(systemSources))
                self.sources["system"] = list()
                if systemSources == None:
                    self.errorLog("The system sources list wasn't successfully retrieved from Airfoil - please check Airfoil's configuration.")
                    self.currentSource = None
                else:
                    for source in systemSources:
                        self.sources["system"].append(self.airfoil.get(source.name))
                        self.sources["map"][self.airfoil.get(source.id)] = self.airfoil.get(source.name)
                        self.sources["typeMap"][self.airfoil.get(source.id)] = "system"
                        #self.debugLog("    %s (%i)" % (self.airfoil.get(source.name), self.airfoil.get(source.id)))
                    theCurrentSource = self.airfoil.current_audio_source.get()
                    if theCurrentSource == None or str(theCurrentSource) == "k.missing_value":
                        self.currentSource = None
                        self.errorLog("The current audio source wasn't successfully retrieved from Airfoil - please check Airfoil's configuration to make sure you have a valid source selected.")
                    else:
                        self.debugLog("Current Source: %s" % str(theCurrentSource))
                        theCurrentSourceId = self.airfoil.get(theCurrentSource.id)
                        self.currentSourceType = self.sources["typeMap"].get(theCurrentSourceId, "none")
                        if theCurrentSource != self.currentSource:
                            if self.pluginPrefs.get("createSourceVar", False):
                                self.debugLog("    updating source var: %s to %s in folder %s" % ("CurrentSource", self.airfoil.get(theCurrentSource.name), self.pluginPrefs["folderId"]))
                                updateVar("CurrentSource", self.airfoil.get(theCurrentSource.name), self.pluginPrefs["folderId"])
                            if self.currentSource != None:
                                # Look up any source change events and execute the triggers
                                for trigger in self.events[kTriggerType_SourceChange]:
                                    indigo.trigger.execute(trigger)
                            self.currentSource = theCurrentSource
                # speakers
                knownSpeakers = self.pluginPrefs.get("speakers",{})
                newKnownSpeakers = indigo.Dict()
                speakers = self.airfoil.speakers.get()
                self.debugLog(u"update: speakers: %s" % unicode(speakers))
                if speakers == None:
                    self.errorLog("The speaker list wasn't successfully retrieved from Airfoil - please check Airfoil's configuration.")
                else:
                    self.speakers = dict()
                    for speaker in speakers:
                        speakerId = "".join(self.airfoil.get(speaker.id).split("@")[0].split(":")[0].split("-"))
                        self.speakers[speakerId] = speaker
                        speakerName = self.airfoil.get(speaker.name)
                        speakerId = u"ID-" + speakerId
                        speakerConnected = self.airfoil.get(speaker.connected)
                        self.debugLog("update: %s (%s) - Connected: %i" % (self.airfoil.get(speaker.name), self.airfoil.get(speaker.id), self.airfoil.get(speaker.connected)))
                        if speakerConnected:
                            connStr = u"connected"
                        else:
                            connStr = u"disconnected"
                        if speakerId in knownSpeakers:
                            if knownSpeakers[speakerId][1] == u"unavailable":
                                if self.pluginPrefs.get("createVars", False):
                                    updateVar(cleanName(speakerName), connStr, self.pluginPrefs["folderId"])
                                for trigger in self.events[kTriggerType_SpeakerChange][kTriggerType_SpeakerBecomesAvailable].values():
                                    if trigger.pluginProps["speakerId"] == speakerId:
                                        indigo.trigger.execute(trigger)
                            if knownSpeakers[speakerId][1] != connStr:
                                if self.pluginPrefs.get("createVars", False):
                                    updateVar(cleanName(speakerName), connStr, self.pluginPrefs["folderId"])
                                if speakerConnected:
                                    for trigger in self.events[kTriggerType_SpeakerChange][kTriggerType_SpeakerBecomesConnected].values():
                                        if trigger.pluginProps["speakerId"] == speakerId:
                                            indigo.trigger.execute(trigger)
                                else:
                                    for trigger in self.events[kTriggerType_SpeakerChange][kTriggerType_SpeakerBecomesDisconnected].values():
                                        if trigger.pluginProps["speakerId"] == speakerId:
                                            indigo.trigger.execute(trigger)
                            del knownSpeakers[speakerId]
                        self.debugLog(u"update: adding to newKnownSpeakers for id: %s value: %s" % (speakerId, unicode((speakerName, connStr))))
                        newKnownSpeakers[speakerId] = (speakerName, connStr)
                    for missingSpeakerKey in knownSpeakers:
                        if knownSpeakers[missingSpeakerKey][1] != u"unavailable":
                            if self.pluginPrefs.get("createVars", False):
                                updateVar(cleanName(knownSpeakers[missingSpeakerKey][0]), u"unavailable", self.pluginPrefs["folderId"])
                            for trigger in self.events[kTriggerType_SpeakerChange][kTriggerType_SpeakerBecomesUnavailable].values():
                                if trigger.pluginProps["speakerId"] == missingSpeakerKey:
                                    indigo.trigger.execute(trigger)
                        missingSpeaker = knownSpeakers[missingSpeakerKey]
                        missingSpeaker[1] = u"unavailable"
                        newKnownSpeakers[missingSpeakerKey] = missingSpeaker
                    self.debugLog(u"update: setting speakers pref to: %s" % unicode(newKnownSpeakers))
                    self.pluginPrefs["speakers"] = newKnownSpeakers
            except Exception, e:
                # Something went wrong so write an error to the log and write the exception to the debug log
                self.errorLog("Update failed. Check to see if Airfoil is functioning correctly and that there is only a single copy of the application on your hard drive.")
                self.debugLog("Update failed with exception:\n%s" % traceback.format_exc(10))
                return
        else:
            self.errorLog("update: airfoil.isrunning() is returning false. Check to see if Airfoil is functioning correctly and that there is only a single copy of the application on your hard drive.")


    ########################################
    def closedPrefsConfigUi(self, valuesDict, userCancelled):
        if not userCancelled:
            self.debug = valuesDict.get("showDebugInfo", False)
            if self.debug:
                indigo.server.log("Debug logging enabled")
            else:
                indigo.server.log("Debug logging disabled")
            if valuesDict.get("createVars", False) or valuesDict.get("createSourceVar",False):
                if "folderId" not in self.pluginPrefs:
                    if "Airfoil" in indigo.variables.folders:
                        myFolder = indigo.variables.folders["Airfoil"]
                    else:
                        myFolder = indigo.variables.folder.create("Airfoil")
                    self.pluginPrefs["folderId"] = myFolder.id
                if valuesDict.get("createVars", False):
                    self.debugLog("    creating speaker vars")
                    speakerList = self.pluginPrefs.get("speakers",{})
                    for speaker in speakerList.itervalues():
                        cleanSpeakerName = cleanName(speaker[0])
                        if cleanSpeakerName not in indigo.variables:
                            updateVar(cleanSpeakerName, value=speaker[1], folder=self.pluginPrefs["folderId"])
                if valuesDict.get("createSourceVar", False):
                    currentSourceName = ""
                    if self.currentSource != None:
                        currentSourceName = self.airfoil.get(self.currentSource.name)
                    updateVar(u"CurrentSource", value=currentSourceName, folder=self.pluginPrefs["folderId"])
            else:
                if "folderId" in self.pluginPrefs:
                    indigo.variables.folder.delete(self.pluginPrefs["folderId"], deleteAllChildren=True)
                    del self.pluginPrefs["folderId"]


    ########################################
    def runConcurrentThread(self):
        try:
            while True:
                if (self.airfoil != None):	# and (self.airfoil.isrunning()):
                    # Check to see if it's started running since last loop and if so
                    # look to see if we need to fire any events
                    if not self.pluginPrefs["isRunning"]:
                        self.pluginPrefs["isRunning"] = True
                        if kTriggerType_AirfoilAvailable in self.events:
                            for trigger in self.events[kTriggerType_AirfoilAvailable]:
                                indigo.trigger.execute(trigger)
                    self.debugLog("runConcurrentThread: update()")
                    if self.debug and self.throttleSkip > 0:
                        if self.throttleCount < self.throttleSkip:
                            self.throttleCount += 1
                        else:
                            self.throttleCount = 0
                            self.update()
                    else:
                        self.update()
                else:
                    if self.airfoil:
                        self.debugLog("runConcurrentThread: Airfoil isn't running")
                    else:
                        self.debugLog("runConcurrentThread: %s" % kAirfoilUnavailableMessage)
                    if self.pluginPrefs["isRunning"]:
                        self.pluginPrefs["isRunning"] = False
                        if kTriggerType_AirfoilUnavailable in self.events:
                            for trigger in self.events[kTriggerType_AirfoilUnavailable]:
                                indigo.trigger.execute(trigger)
                self.sleep(2)
        except self.StopThread:
            pass

    ########################################
    # UI Validate, Close, and Actions defined in Actions.xml:
    ########################################
    def validateActionConfigUi(self, valuesDict, typeId, devId):
        fail = False
        descString = u"airfoil: "
        if typeId == "connectToSpeaker":
            descString += u"connect to speaker " + self.pluginPrefs["speakers"]["ID-"+valuesDict['speaker']][0]
        elif typeId == "disconnectFromSpeaker":
            descString += u"disconnect from speaker " + self.pluginPrefs["speakers"]["ID-"+valuesDict['speaker']][0]
        elif typeId == "toggleSpeaker":
            descString += u"toggle speaker " + self.pluginPrefs["speakers"]["ID-"+valuesDict['speaker']][0]
        elif typeId == "changeAudioSource":
            errorMsgDict = indigo.Dict()
            if valuesDict["sourceType"] == "system":
                descString += u"change audio source to System Audio"
            elif valuesDict["sourceType"] == "device":
                if valuesDict.get("devSource", "") == "":
                    errorMsgDict['devSource'] = u"You must select a valid source name."
                    return (False, valuesDict, errorMsgDict)
                descString += u"change audio source to " + valuesDict['devSource']
            else:
                if valuesDict.get("appSource", "") == "":
                    errorMsgDict['appSource'] = u"You must select a valid source name."
                    return (False, valuesDict, errorMsgDict)
                descString += u"change audio source to " + valuesDict['appSource']
        elif (typeId == "setVolume") or (typeId == "increaseVolume") or (typeId == "decreaseVolume"):
            errorMsgDict = indigo.Dict()
            if len(valuesDict.get("speakerIds", None)) < 1:
                errorMsgDict["speakerIds"] = u"You must select at least one speaker"
                fail = True
            try:
                theNumber = int(valuesDict.get("volume", "-1"))
            except ValueError:
                theNumber = -1
            if (theNumber < 0) or (theNumber > 100):
                errorMsgDict["volume"] = u"The number must be an integer between 0 and 100"
                valuesDict["volume"] = "0"
                fail = True
            if typeId == "setVolume":
                descString += u"set volume to " + unicode(theNumber)
            elif typeId == "increaseVolume":
                descString += u"increase volume by " + unicode(theNumber)
            else:
                descString += u"decrease volume by " + unicode(theNumber)
            valuesDict["volume"] = theNumber
        if fail:
            return (False, valuesDict, errorMsgDict)
        self.debugLog(u"description string: " + descString)
        valuesDict['description'] = descString
        return (True, valuesDict)

    ####################
    def sourceList(self, filter="", valuesDict=None, typeId="", targetId=0):
        self.debugLog("sourceList called with filter: %s" % (filter,))
        returnList = list()
        for source in self.sources[filter]:
            returnList.append((source,source))
        return returnList

    ########################################
    # Menu Methods
    ########################################
    def toggleDebugging(self):
        if self.debug:
            indigo.server.log("Turning off debug logging")
            self.pluginPrefs["showDebugInfo"] = False
        else:
            indigo.server.log("Turning on debug logging")
            self.pluginPrefs["showDebugInfo"] = True
        self.debug = not self.debug


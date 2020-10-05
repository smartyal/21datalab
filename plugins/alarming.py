#21datalabplugin
from system import __functioncontrolfolder
import zeep
import json
from utils import str_lim

alarmMessage = {"name":"alarmMessage","type":"alarm","children":[
        {"name": "text", "type":"variable","value":"this is the alarm message text"},
        {"name": "level", "type":"variable","value":"medium"},
        {"name": "confirmed", "type":"variable","value":False},
        {"name": "startTime", "type": "variable", "value": "2020-10-01T08:00:00+02:00"},
        {"name": "endTime", "type": "variable", "value": None},
        {"name": "confirmTime", "type": "variable", "value": "2020-10-01T18:00:00+02:00"},
        {"name": "mustEscalate", "type": "variable", "value": False}
    ]
}

sendEmailWsdl = {
     "name":"sendEmail",
     "type":"function",
     "functionPointer":"alarming.send_email_wsdl",
     "autoReload":True,
     "children":[
        {"name":"URL","type":"const","value":"http://domain:port/sendapp?wsdl"},
        {"name":"fromAddress","type":"variable","value":"noreply@domain.com"},
        {"name":"toAddress","type":"variable","value":"receiver@domain.com"},
        {"name":"subject","type":"variable","value":"alarm email from 21data workbench"},
        {"name":"body","type":"variable","value":"this is an automatic mail from the 21data workbench. re-thinking self service analytics"},
        __functioncontrolfolder
     ]
}

checkMails = {
    "name": "checkMails",
    "type": "function",
    "functionPointer": "alarming.check_mail_sending",
    "autoReload": True,
    "children": [
        {"name": "messages", "type": "referencer"},
        {"name": "sendMailFunction","type":"referencer"},
        __functioncontrolfolder
    ]

}


alarmFolder = {
    "name":"alarms","type":"folder","children":[
        {"name":"messages","type":"folder"},
        checkMails,
        sendEmailWsdl,
        {
            "name": "emailObserver","type": "observer", "children": [
                {"name": "enabled", "type": "const", "value": True},  # turn on/off the observer
                {"name": "triggerCounter", "type": "variable", "value": 0},  # increased on each trigger
                {"name": "lastTriggerTime", "type": "variable", "value": ""},  # last datetime when it was triggered
                {"name": "targets", "type": "referencer","references":["alarms.messages"]},  # pointing to the nodes observed
                {"name": "properties", "type": "const", "value": ["children","value"]},
                # properties to observe [“children”,“value”, “forwardRefs”]
                {"name": "onTriggerFunction", "type": "referencer","references":["alarms.checkMails"]},  # the function(s) to be called when triggering
                {"name": "triggerSourceId", "type": "variable"},
                # the sourceId of the node which caused the observer to trigger
                {"name": "hasEvent", "type": "const", "value": True},
                # set to event string iftrue if we want an event as well
                {"name": "eventString", "type": "const", "value": "alarms.update"},  # the string of the event
            ]
        }
    ]
}
#this is executed on load of the library!
############################################
alarmFolder["children"][1]["children"][0]["references"]=["alarms.messages"]
alarmFolder["children"][1]["children"][1]["references"]=["alarms.sendEmail"]


################################################
def send_email_wsdl(functionNode):
    """
        send email via wsdl service
    """
    logger = functionNode.get_logger()
    logger.info(f">>>> in send_email_wsdl {functionNode.get_browse_path()}")
    wsdl = functionNode.get_child("URL").get_value()
    client = zeep.Client(wsdl=wsdl)
    try:

        req = {'FromAddress': functionNode.get_child("fromAddress").get_value(),
           'ToAddresses': functionNode.get_child("toAddress").get_value(),
           'Subject':functionNode.get_child("subject").get_value(),
           'Body': functionNode.get_child("body").get_value()}
        logger.info(f"send email {str_lim(req,200)}")
        response = client.service.SvcSendMail(**req) #we dont' get any result here
        logger.debug(r"send mail response {response}")
    except Exception as ex:
        logger.error(r"send_email_wsdl problem {ex}")
        return False

    return True


def check_mail_sending(functionNode):
    """
        check if we need to send any mail
    """
    logger = functionNode.get_logger()
    model = functionNode.get_model()
    logger.info(f">>>> in check_mail_sending {functionNode.get_browse_path()}")
    sendMailFunction = functionNode.get_child("sendMailFunction").get_target()
    messages = functionNode.get_child("messages").get_leaves()
    for msg in messages:
        mustSend= msg.get_child("mustEscalate")
        if mustSend and mustSend.get_value()== True:
            #prepare a mail from the message
            body = {child.get_name():child.get_value() for child in msg.get_children()}
            logger.debug(f"email body {body}")
            sendMailFunction.get_child("body").set_value(json.dumps(body,indent=4))
            try:
                model.disable_observers()
                mustSend.set_value(False) # flag this message as done
            finally:
                model.enable_observers()
            #now send the email and wait for ready
            sendMailFunction.execute_synchronous()

    return True


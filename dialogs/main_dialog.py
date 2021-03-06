# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from botbuilder.dialogs import (
    ComponentDialog,
    WaterfallDialog,
    WaterfallStepContext,
    DialogTurnResult,
)
from botbuilder.dialogs.prompts import TextPrompt, PromptOptions
from botbuilder.core import MessageFactory, TurnContext
from botbuilder.schema import InputHints

from product_details import ProductDetails
from main_details import MainDetails
from recognizer import ShoppingRecognizer
from helpers.luis_helper import LuisHelper, Intent
from .recommend_dialog import RecommendDialog
from .adjust_dialog import AdjustDialog
from helpers.ok_helper import is_ok

import os




class MainDialog(ComponentDialog):
    def __init__(
        self, luis_recognizer: ShoppingRecognizer, recommend_dialog: RecommendDialog, adjust_dialog: AdjustDialog
    ):
        super(MainDialog, self).__init__(MainDialog.__name__)

        self._luis_recognizer = luis_recognizer
        self._recommend_dialog_id = recommend_dialog.id
        self._adjust_dialog_id = adjust_dialog.id


        self.add_dialog(TextPrompt(TextPrompt.__name__))
        self.add_dialog(recommend_dialog)
        self.add_dialog(adjust_dialog)
        self.add_dialog(
            WaterfallDialog(
                "WFDialog", [self.intro_step, self.act_step, self.adjust_step, self.final_step]
            )
        )
        self.add_dialog(
            WaterfallDialog(
                "STARTDialog", [self.start_step]
            )
        )

        self.initial_dialog_id = "STARTDialog"
        self.WF_id = "WFDialog"

    async def start_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
            return await step_context.begin_dialog(self.WF_id, options=ProductDetails())


    async def intro_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        if not self._luis_recognizer.is_configured:
            await step_context.context.send_activity(
                MessageFactory.text(
                    "NOTE: LUIS is not configured. To enable all capabilities, add 'LuisAppId', 'LuisAPIKey' and "
                    "'LuisAPIHostName' to the appsettings.json file.",
                    input_hint=InputHints.ignoring_input,
                )
            )

            return await step_context.next(None)
        '''
        message_text = (
            str(step_context.options)
            if step_context.options
            else "您好！有什么能帮到您的吗？"
        )
        '''
        message_text = (
            "您好！有什么能帮到您的吗？"
        )

        prompt_message = MessageFactory.text(
            message_text, message_text, InputHints.expecting_input
        )

        return await step_context.prompt(
            TextPrompt.__name__, PromptOptions(prompt=prompt_message)
        )



    async def act_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        if not self._luis_recognizer.is_configured:
            print('not self._luis_recognizer.is_configured')
            # LUIS is not configured, we just run the BookingDialog path with an empty BookingDetailsInstance.
            return await step_context.begin_dialog(
                self._recommend_dialog_id, ProductDetails()
            )

        # Call LUIS and gather any potential booking details. (Note the TurnContext has the response to the prompt.)
        intent, luis_result = await LuisHelper.execute_luis_query(
            self._luis_recognizer, step_context.context
        )

        if intent == Intent.ASK.value and luis_result:
            #print('intent == Intent.ASK.value and luis_result')
            return await step_context.begin_dialog(self._recommend_dialog_id, options=ProductDetails())

        else:
            didnt_understand_text = (
                "这个我搞不懂。"+str(intent)+Intent.ASK.value+str(luis_result)
            )
            didnt_understand_message = MessageFactory.text(
                didnt_understand_text, didnt_understand_text, InputHints.ignoring_input
            )
            return await step_context.context.send_activity(didnt_understand_message)

    async def adjust_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        # If the child dialog ("BookingDialog") was cancelled or the user failed to confirm,
        # the Result here will be null.
        if not self._luis_recognizer.is_configured:
            # LUIS is not configured, we just run the BookingDialog path with an empty BookingDetailsInstance.
            return await step_context.begin_dialog(
                self._recommend_dialog_id, ProductDetails()
            )



        if step_context.context is not None:
            msg_txt = (
                f"您对这个推荐结果满意吗？"
            )

            message = MessageFactory.text(msg_txt, msg_txt, InputHints.expecting_input)
            return await step_context.prompt(
                TextPrompt.__name__, PromptOptions(prompt=message)
            )

    async def final_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:

        print(step_context.context.activity)
        details = step_context.context.activity.text
        ok = is_ok(details)

        if ok:
            prompt_message = "好的，我还能帮到什么吗？"    
            return await step_context.replace_dialog(self.id, prompt_message)
        else:
            with open(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+'/save/satisfied.txt','w+') as f:
                is_satisfied = f.read()
            if is_satisfied != 'Yes':
                print(1)
                return await step_context.begin_dialog(self._adjust_dialog_id)


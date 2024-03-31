# encoding:utf-8

import plugins
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from channel.chat_message import ChatMessage
from common.log import logger
from plugins import *
from config import conf
import requests
import json


@plugins.register(
    name="dingtalkDuoweibiao",
    desire_priority=-2,
    hidden=True,
    desc="A plugin that Structure the supplier quotation information and insert it into a multidimensional table。",
    version="0.1",
    author="chenfrigate",
)
class dingtalkDuoweibiao(Plugin):
    def __init__(self):
        super().__init__()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        self.handlers[Event.ON_DECORATE_REPLY] = self.on_decorate_reply
        logger.info("[dintalkDuoweibiao] inited")
        self.config = super().load_config()

    def on_handle_context(self, e_context: EventContext):
        if e_context["context"].type not in [
            ContextType.TEXT,
            ContextType.JOIN_GROUP,
            ContextType.PATPAT,
            ContextType.EXIT_GROUP
        ]:
            return
        if e_context["context"].type == ContextType.JOIN_GROUP:
            if "group_welcome_msg" in conf():
                reply = Reply()
                reply.type = ReplyType.TEXT
                reply.content = conf().get("group_welcome_msg", "")
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑
                return
            e_context["context"].type = ContextType.TEXT
            msg: ChatMessage = e_context["context"]["msg"]
            e_context["context"].content = f'请你随机使用一种风格说一句问候语来欢迎新用户"{msg.actual_user_nickname}"加入群聊。'
            e_context.action = EventAction.BREAK  # 事件结束，进入默认处理逻辑
            if not self.config or not self.config.get("use_character_desc"):
                e_context["context"]["generate_breaked_by"] = EventAction.BREAK
            return
        
        if e_context["context"].type == ContextType.EXIT_GROUP:
            if conf().get("group_chat_exit_group"):
                e_context["context"].type = ContextType.TEXT
                msg: ChatMessage = e_context["context"]["msg"]
                e_context["context"].content = f'请你随机使用一种风格跟其他群用户说他违反规则"{msg.actual_user_nickname}"退出群聊。'
                e_context.action = EventAction.BREAK  # 事件结束，进入默认处理逻辑
                return
            e_context.action = EventAction.BREAK
            return
            
        if e_context["context"].type == ContextType.PATPAT:
            e_context["context"].type = ContextType.TEXT
            msg: ChatMessage = e_context["context"]["msg"]
            e_context["context"].content = f"请你随机使用一种风格介绍你自己，并告诉用户输入#help可以查看帮助信息。"
            e_context.action = EventAction.BREAK  # 事件结束，进入默认处理逻辑
            if not self.config or not self.config.get("use_character_desc"):
                e_context["context"]["generate_breaked_by"] = EventAction.BREAK
            return

        #content = e_context["context"].content
        content = e_context["context"].content[:]
        logger.debug("[Hello] on_handle_context. content: %s" % content)
      
        prompt = """请你按输出示例的格式返回输入内容，并在最前面加上【插入多维表】这个短语：
            输出示例：{"Entry_log": {"Entry_Time": "2024年3月31日","Inputter_Name": "chen"},"Product_Price":"10000", "Product_Specifications": "A100","Product_Name": "机器", "Supplier_Name": "华为"}
            输出示例字段说明：Entry_Time的内容是今天，Inputter_Name说明这个信息是谁提供的，Product_Price是产品价格，Product_Specifications是产品型号，Product_Name是产品名称，Supplier_Name是供应商的名称。
            输入内容："""+ content
        e_context["context"].type = ContextType.TEXT
        msg: ChatMessage = e_context["context"]["msg"]
        e_context["context"].content = prompt
        e_context.action = EventAction.BREAK  # 事件结束，进入默认处理逻辑
        if not self.config or not self.config.get("use_character_desc"):
            e_context["context"]["generate_breaked_by"] = EventAction.BREAK
        return

    def on_decorate_reply(self, e_context: EventContext):
        if e_context["reply"].type not in [ReplyType.TEXT]:
            return
        reply = e_context["reply"]
        content = reply.content
        if content.startswith("【插入多维表】"):
            reply.type = ReplyType.TEXT
            reply.content = content
        reply = Reply(ReplyType.INFO, "已触发了多维表插入: \n" + content)
        e_context["reply"] = reply
        e_context.action = EventAction.CONTINUE
        # Webhook的URL
        webhook_url = 'https://connector.dingtalk.com/webhook/trigger/data/sync?webhookId=10295812bc61213c6a90000f'

        # 要传递的参数，这里使用JSON格式
        # 找到分隔符【插入多维表】的位置并分割字符串
        split_index = content.find("【插入多维表】")
        if split_index != -1:
            after_separator = content[split_index + len("【插入多维表】"):]
        else:
            after_separator = content

        # 将分割后的内容转换为字典
        data = json.loads(after_separator)
        # 将参数转换为JSON格式的字符串
        json_data = json.dumps(data)
        #print("json_data="+json_data)

        # 发送POST请求
        response = requests.post(webhook_url, headers={'Content-Type': 'application/json'}, data=json_data)

        # 检查请求是否成功
        if response.status_code == 200:
            print('Webhook triggered successfully.')
        else:
            print('Failed to trigger webhook.')

        return
            
    def get_help_text(self, **kwargs):
        help_text = "给我供应商的报价信息，我帮你插入多维表\n"
        return help_text

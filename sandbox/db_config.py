from file_db import FileDBMeta


class NormMeta(FileDBMeta):
    def __init__(self):
        super(NormMeta,self).__init__('norm', 'ext_id')

    def on_update(self, db, new_norm):
        print("NormMeta.on_update")
        from llm_tasks import get_llm_task_map, NotEnoughData
        norm_map = get_llm_task_map()['norm']
        for attr in norm_map.keys():
            try:
                if attr not in norm.keys():
                    if norm_map[attr].check(new_norm):
                        llm_task = norm_map[attr].generate(new_norm)
                        db.write(llm_task)
            except NotEnoughData:
                pass


class LLMTaskMeta(FileDBMeta):
    def __init__(self):
        super(LLMTaskMeta,self).__init__('llm_task', 'task_key')

    def on_update(self, db, new_obj):
        print("LLMTaskMeta.on_update")
        pass


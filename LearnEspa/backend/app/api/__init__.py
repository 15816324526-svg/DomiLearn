

#FastAPI 在程序启动时会读取这些装饰器和函数类型：
#@router.post("/rounds/{round_id}/answers")
#def submit_answer(
#    round_id: str,
#    payload: AnswerRequest,
#    service: ImitationService = Depends(get_service),
#):
#它自动得到：
#请求方法     POST
#地址         /api/imitation/rounds/{round_id}/answers
#路径参数     round_id
#JSON 格式    AnswerRequest
#所需服务     get_service() 的返回值
#返回结果     Python 字典转 JSON

#你没有看到手写的“解析 HTTP、解析 JSON、检查字段、调用函数、序列化结果”，
#是因为这些通用工作由 FastAPI 完成了。
#框架的价值就在这里。
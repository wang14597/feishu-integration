import aiohttp

from download_wiki_and_upload_to_gcs.client import AUTH_INFO
from download_wiki_and_upload_to_gcs.conf import BASE_URL


async def get(url, **kwargs):
    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL + url, **kwargs) as response:
            return await response.json()


async def post(url, **kwargs):
    async with aiohttp.ClientSession() as session:
        async with session.post(BASE_URL + url, **kwargs) as response:
            return await response.json()


async def get_tenant_access_token():
    request = await post("/auth/v3/tenant_access_token/internal", data=AUTH_INFO)
    return request["tenant_access_token"]


# def get_download_task_info_new(client, ticket, node):
#     loop = asyncio.get_event_loop()  # 获取当前事件循环
#     tenant_access_token = loop.run_until_complete(get_tenant_access_token())  # 在现有事件循环中执行异步函数
#     header = {"Authorization": f"Bearer {tenant_access_token}"}
#     url = f"/drive/v1/export_tasks/{ticket}?token={node.obj_token}"
#     rep = loop.run_until_complete(get(url, headers=header))
#     return rep["data"]['result']['file_token']


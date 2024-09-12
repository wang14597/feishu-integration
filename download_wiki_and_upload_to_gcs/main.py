import time
from concurrent.futures import ThreadPoolExecutor

import lark_oapi as lark
from google.cloud import storage
from lark_oapi.api.drive.v1 import *
from lark_oapi.api.wiki.v2 import *

from download_wiki_and_upload_to_gcs.client import create_lark_client
from download_wiki_and_upload_to_gcs.conf import SERVICE_ACCOUNT, WIKI_NAME, BUCKET_NAME
from download_wiki_and_upload_to_gcs.utils import get_last_success_time, update_last_success_time


def get_space_id(client: lark.client.Client, wiki_name) -> str:
    request: ListSpaceRequest = ListSpaceRequest.builder().build()
    response: ListSpaceResponse = client.wiki.v2.space.list(request)
    for i in response.data.items:
        if i.name == wiki_name:
            return i.space_id
    return ""


def get_wiki_nodes(client, space_id: str) -> list[node.Node]:
    request: ListSpaceNodeRequest = ListSpaceNodeRequest.builder().space_id(space_id).build()
    response: ListSpaceNodeResponse = client.wiki.v2.space_node.list(request)
    return response.data.items


def get_updated_nodes(items: list[node.Node], last_success_time: str) -> list[str]:
    r = []
    for n in items:
        if int(n.obj_edit_time) > int(last_success_time):
            r.append(n.node_token)
    return r


def get_wiki_space_node(client, node_token: str):
    request: GetNodeSpaceRequest = GetNodeSpaceRequest.builder().token(node_token).build()
    response: GetNodeSpaceResponse = client.wiki.v2.space.get_node(request)
    return response.data


def create_download_task(client, node: node.Node) -> CreateExportTaskResponseBody:
    export_task = ExportTask.builder().file_extension("pdf").token(node.obj_token).type(node.obj_type).build()
    request: CreateExportTaskRequest = CreateExportTaskRequest.builder().request_body(export_task).build()
    response: CreateExportTaskResponse = client.drive.v1.export_task.create(request)
    return response.data


def get_download_task_info(client, ticket, node: node.Node) -> GetExportTaskResponseBody:
    # TODO job_status must be 0
    # 根据创建导出任务返回的导出任务 ID（ticket）轮询导出任务结果，并返回导出文件的 token。
    request: GetExportTaskRequest = GetExportTaskRequest.builder() \
        .ticket(ticket) \
        .token(node.obj_token) \
        .build()
    response: GetExportTaskResponse = client.drive.v1.export_task.get(request)
    while response.data.result.job_status != 0:
        time.sleep(5)
        response: GetExportTaskResponse = client.drive.v1.export_task.get(request)
    return response.data


def download_file(client, file_token):
    request: DownloadExportTaskRequest = DownloadExportTaskRequest.builder().file_token(file_token).build()
    response: DownloadExportTaskResponse = client.drive.v1.export_task.download(request)

    if not response.success():
        lark.logger.error(
            f"client.drive.v1.export_task.download failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}")
        return
    return response.file


def upload_to_gcs(storage_client, bucket_name, file_obj, destination_blob_name):
    bucket = storage_client.bucket(bucket_name)
    # TODO 默认pdf
    blob = bucket.blob(destination_blob_name + ".pdf")
    file_obj.seek(0)
    blob.upload_from_file(file_obj)


def download_and_upload(client, storage_client, node):
    n = get_wiki_space_node(client, node)
    task = create_download_task(client, n.node)
    task_info = get_download_task_info(client, task.ticket, n.node)
    bytes_io = download_file(client, task_info.result.file_token)
    upload_to_gcs(storage_client, BUCKET_NAME, bytes_io, task_info.result.file_name)


def main():
    last_success_time = get_last_success_time()
    try:
        client = create_lark_client()
        storage_client = storage.Client.from_service_account_json(SERVICE_ACCOUNT)
        space_id = get_space_id(client, WIKI_NAME)
        space_nodes = get_wiki_nodes(client, space_id)
        update_last_success_time("%d" % time.time())
        updated_nodes = get_updated_nodes(space_nodes, last_success_time)
        with ThreadPoolExecutor(max_workers=4) as executor:
            for node in updated_nodes:
                executor.submit(download_and_upload, client, storage_client, node)
    except Exception as e:
        lark.logger.error(e)
        update_last_success_time(last_success_time)


if __name__ == '__main__':
    main()

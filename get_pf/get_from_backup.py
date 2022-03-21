# Загружаем задачи, комментарии и сопутствующую информацию из АПИ ПФ

import json
import os
import requests
import xmltodict
from lxml import etree, objectify

from lib import format_phone
from hide_data import URL, USR_Tocken, PSR_Tocken, PF_ACCOUNT

PF_BACKUP_DIRECTORY = '../../hr_pf/get_pf/planfix-data-202202182037'
PF_HEADER = {"Accept": 'application/xml', "Content-Type": 'application/xml'}
RELOAD_ALL_FROM_API = False

def create_record(id, model, sources):
    """  Создаем запись БД flectra  """
    record = objectify.Element('record', id=id, model=model)
    fields = []
    i = -1
    for source in sources:
        i += 1
        if str(source).endswith('_id'):
            fields.append(objectify.SubElement(record, 'field', name=source, ref=sources[source]))
        elif source and sources[source]:
            fields.append(objectify.SubElement(record, 'field', name=source))
            fields[i]._setText(sources[source])
        else:
            print(id, source, sources[source])
    return record

def load_statuses_from_api():
    """ Загружаем список процессов и список статусов по каждому процессу """
    processes = {}
    statuses = {}
    answer = requests.post(
        URL,
        headers=PF_HEADER,
        data='<request method="taskStatus.getSetList"><account>' + PF_ACCOUNT +
             '</account></request>',
        auth=(USR_Tocken, PSR_Tocken)
    )
    processes_xml = xmltodict.parse(answer.text)['response']['taskStatusSets']['taskStatusSet']
    for process in processes_xml:
        processes['pr_' + process['id']] = {
            'name': process['name'],
            'id_pf': process['id']
        }
        answer = requests.post(
            URL,
            headers=PF_HEADER,
            data='<request method="taskStatus.getListOfSet"><account>' + PF_ACCOUNT +
                 '</account><taskStatusSet><id>' + str(process['id']) + '</id></taskStatusSet></request>',
            auth=(USR_Tocken, PSR_Tocken)
        )
        statuses_xml = xmltodict.parse(answer.text)['response']['taskStatuses']['taskStatus']
        for status in statuses_xml:
            statuses['st_' + status['id']] = {
                'name': status['name'],
                'id_pf': status['id'],
                'process_id': 'pr_' + process['id']
            }
    return processes, statuses


def load_fields_name_from_api():
    """ Загружаем из шаблонов fields_id2names[id]=название_полея"""
    fields_id2names = {}
    i = 1
    while True:
        answer = requests.post(
            URL,
            headers=PF_HEADER,
            data='<request method="task.getList"><account>' + PF_ACCOUNT +
                 '</account><target>template</target><pageSize>100</pageSize><pageCurrent>' + str(i) +
                 '</pageCurrent></request>',
            auth=(USR_Tocken, PSR_Tocken)
        )
        if answer.text.find('count="0"/></response>') > -1:
            break
        else:
            templates = xmltodict.parse(answer.text)['response']['tasks']['task']
            for template in templates:
                if template.get('customData', None):
                    if template['customData'].get('customValue', None):
                        if str(type(template['customData']['customValue'])).find('list') > -1:
                            for field in template['customData']['customValue']:
                                fields_id2names[int(field['field']['id'])] = field['field']['name']
                        else:
                            field = template['customData']['customValue']
                            fields_id2names[int(field['field']['id'])] = field['field']['name']
        i += 1
    return fields_id2names


def load_all_tasks_from_api():
    """ Загружаем все задачи из АПИ"""
    i = 1
    tasks = []
    while True:
        answer = requests.post(
            URL,
            headers=PF_HEADER,
            data='<request method="task.getList"><account>' + PF_ACCOUNT +
                 '</account><pageSize>100</pageSize><pageCurrent>' + str(i) +
                 '</pageCurrent></request>',
            auth=(USR_Tocken, PSR_Tocken)
        )
        if answer.text.find('count="0"/></response>') > -1:
            break
        else:
            tasks += xmltodict.parse(answer.text)['response']['tasks']['task']
        i += 1
    with open(os.path.join(PF_BACKUP_DIRECTORY, 'tasks_full.json'), 'w') as write_file:
        json.dump(tasks, write_file, ensure_ascii=False)
    return


if __name__ == "__main__":
    if RELOAD_ALL_FROM_API:
        load_all_tasks_from_api()

    # Загружаем список процессо и статусов из АПИ
    processes, statuses = load_statuses_from_api()

    # Загружаем бэкап комментариев
    #with open(os.path.join(PF_BACKUP_DIRECTORY, 'actions.json'), 'r') as read_file:
    #    actions_from_json = json.load(read_file)

    # Загружаем данные по задачам из файла, полученного из АПИ
    with open(os.path.join(PF_BACKUP_DIRECTORY, 'tasks_full.json'), 'r') as read_file:
        tasks_from_json = json.load(read_file)

    # Названия полей и id загружаем в процессе

    template_fields = {}
    fields_fills = {}
    stages = {}
    for task in tasks_from_json:
        if task['type'] != 'template':
            if task.get('customData', None):
                if task['customData'].get('customValue', None):
                    if str(type(task['customData']['customValue'])).find('list') > -1:
                        for field in task['customData']['customValue']:
                            if not template_fields.get('tpl_field_' + field['field']['id']):
                                template_fields['tpl_field_' + field['field']['id']] = {
                                    'name': field['field']['name'],
                                    'template_filed_id_pf': field['field']['id']
                                }
                            fields_fills[task['general'] + '_' + field['field']['id']] = {
                                'task_id': 'task_' +  task['general'],
                                'template_field_name_id': 'tpl_field_' + field['field']['id'],
                                'text': field.get('text',''),
                                'value': field.get('value',''),
                            }
                    else:
                        field = task['customData']['customValue']
                        if not template_fields.get('tpl_field_' + field['field']['id']):
                            template_fields['tpl_field_' + field['field']['id']] = {
                                'name': field['field']['name'],
                                'template_filed_id_pf': field['field']['id']
                            }
                        fields_fills[task['general'] + '_' + field['field']['id']] = {
                            'task_id': 'task_' + task['general'],
                            'template_field_name_id': 'tpl_field_' + field['field']['id'],
                            'text': field.get('text', ''),
                            'value': field.get('value', ''),
                        }


    # Заголовок xml
    flectra_root = objectify.Element('flectra')
    flectra_data = objectify.SubElement(flectra_root, 'data')

    for template_field in template_fields:
        record = create_record(str(template_field), 'docflow.field.template', template_fields[template_field])
        flectra_data.append(record)

    for field_fill in fields_fills:
        record = create_record(field_fill, 'docflow.field.template', fields_fills[field_fill])
        flectra_data.append(record)

    # удаляем все lxml аннотации.
    objectify.deannotate(flectra_root)
    etree.cleanup_namespaces(flectra_root)

    # конвертируем все в привычную нам xml структуру.
    obj_xml = etree.tostring(flectra_root,
                             pretty_print=True,
                             xml_declaration=True,
                             encoding='UTF-8'
                             )

    try:
        with open("../data/docflow_data.xml", "wb") as xml_writer:
            xml_writer.write(obj_xml)
    except IOError:
        pass

# Загружаем задачи, комментарии и сопутствующую информацию из АПИ ПФ

import json
import os
import requests
import xmltodict
from lxml import etree, objectify
import csv
from datetime import datetime, timedelta

from lib import format_phone, l
from hide_data import URL, USR_Tocken, PSR_Tocken, PF_ACCOUNT
from refresh_all_from_api import reload_all, api_load_from_list

PF_BACKUP_DIRECTORY = '../../hr_pf/get_pf/current'
PF_DATA_DIRECTORY = '../../hr_pf/data'
PF_HEADER = {"Accept": 'application/xml', "Content-Type": 'application/xml'}
RELOAD_ALL_FROM_API = False


def create_record(id, model, sources):
    """  Создаем запись БД flectra  """
    record = objectify.Element('record', id=id, model=model)
    fields = []
    i = -1
    for source in sources:
        if (str(source).endswith('_id') or str(source).endswith('_uid')) and sources[source]:
            i += 1
            fields.append(objectify.SubElement(record, 'field', name=source, ref=sources[source]))
        elif str(source).endswith('_ids') and str(type(sources[source])).find('list') > -1:
            i += 1
            attr = "[(6, 0, [ ref('" + "'), ref('".join(sources[source]) + "')])]"
            fields.append(objectify.SubElement(
                record,
                'field',
                name=source,
                eval="[(6, 0, [ ref('" + "'), ref('".join(sources[source]) + "')])]"))
        elif source and sources[source]:
            i += 1
            fields.append(objectify.SubElement(record, 'field', name=source))
            fields[i]._setText(str(sources[source]))
        else:
            pass
            # print(id, source, sources[source])
    return record


def dict_key(key, test_dict):
    """ Проверяет наличие test_dict[key]. Если есть - возвращает key, если нет - '' """
    if test_dict.get(key ,None):
        return key
    else:
        return ''


def check_parent_id(tid, tdict):
    if tid:
        if tdict.get(int(tdict[int(tid)]['parent']['id']), None):
            if int(tid) > int(tdict[int(tid)]['parent']['id']):
                return int(tdict[int(tid)]['parent']['id'])
            else:
                return None
        else:
            return None
    else:
        return None


def load_projects_from_api():
    """ Загружаем проекты ПФ """
    projects = []
    i = 1
    while True:
        answer = requests.post(
            URL,
            headers=PF_HEADER,
            data='<request method="project.getList"><account>' + PF_ACCOUNT +
                 '</account><pageSize>100</pageSize><pageCurrent>' + str(i) +
                 '</pageCurrent></request>',
            auth=(USR_Tocken, PSR_Tocken)
        )
        if answer.text.find('count="0"/></response>') > -1:
            break
        else:
            if str(type(xmltodict.parse(answer.text)['response']['projects']['project'])).find('list'):
                projects += xmltodict.parse(answer.text)['response']['projects']['project']
            else:
                projects += [xmltodict.parse(answer.text)['response']['projects']['project']]
        i += 1
    with open('project_full.json', 'w') as write_file:
        json.dump(projects, write_file, ensure_ascii=False)
    return projects


def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█'):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end = '\r')
    # Print New Line on Complete
    if iteration == total:
        print()

def chk_users(id):
    if int(id) in users:
        return str(id)
    else:
        return '5309784'


if __name__ == "__main__":
    # Перезагружаем всё в файлы
    if RELOAD_ALL_FROM_API:
        reload_all()

    # НЕ Загружаем бэкап задач из бэкапа ПФ стандартными средствами - глюкавый
    all_tasks_ids = set()
    standart_backup = """
    with open(os.path.join(PF_BACKUP_DIRECTORY, 'tasks.json'), 'r') as read_file:
        tasks_from_pf_backup = json.load(read_file)
    for task in tasks_from_pf_backup:
        all_tasks_ids.add(int(task['id']))
    """

    # Загружаем бэкап задач из выгрузки всех задач (task.getMulti скорректированной task.get) через АПИ ПФ
    tasks_full = {}
    with open(os.path.join(PF_BACKUP_DIRECTORY, 'tasks_full.json'), 'r') as read_file:
        tasks_full_str = json.load(read_file)
    for task in tasks_full_str:
        all_tasks_ids.add(int(task))
        tasks_full[int(task)] = tasks_full_str[task]
    print('Из сохраненных полных (task.getMulti):', len(tasks_full))

    # Бэкап задач из выгрузки списка задач (task.getList)
    tasks_short = {}
    with open(os.path.join(PF_BACKUP_DIRECTORY, 'tasks_short.json'), 'r') as read_file:
        tasks_short_str = json.load(read_file)
    for task in tasks_short_str:
        all_tasks_ids.add(int(task))
        tasks_short[int(task)] = tasks_short_str[task]
    print('Из сохраненных задач (task.getList):', len(tasks_short))

    # id загруженных в модуле hr_pf юзеров и сотрудников
    with open(os.path.join(PF_BACKUP_DIRECTORY, 'users_full.json'), 'r') as read_file:
        users_loaded = json.load(read_file)
    users = tuple([int(x) for x in users_loaded.keys()])

    # Процессы (project.project)
    with open(os.path.join(PF_BACKUP_DIRECTORY, 'processes_full.json'), 'r') as read_file:
        processes = json.load(read_file)
    processes4flectra = {}
    for process in processes:
        processes4flectra['pr_' + str(process)] = {
            'name': processes[process]['name'],
            'id_pf': process,
        }

    # Статусы
    with open(os.path.join(PF_BACKUP_DIRECTORY, 'statuses_flectra.json'), 'r') as read_file:
        statuses4flectra = json.load(read_file)

    # Шаблоны задач
    with open(os.path.join(PF_BACKUP_DIRECTORY, 'tasktemplates_full.json'), 'r') as read_file:
        tasktemplates = json.load(read_file)
    tasktemplates4flectra = {}
    for tasktemplate in tasktemplates:
        tasktemplates4flectra['tt_' + str(tasktemplate)] = {
            'name': tasktemplates[tasktemplate]['title'],
            'id_pf': tasktemplates[tasktemplate]['id'],
            'id_pf_general': tasktemplates[tasktemplate]['general']
        }

    # Загружаем данные по задачам из файла, полученного из АПИ
    tasks_from_json = list(tasks_full.values())[70000:70100]
    tasks_from_json_ids = tuple(list(tasks_full.keys())[70000:70100])

    # Названия полей и id загружаем в процессе
    template_fields = {}
    fields_fills = {}
    stages = {}
    tasks = {}
    tasks_from_json_dict = {}
    for task in tasks_from_json:
        if task['type'] == 'task':
            tasks_from_json_dict[int(task['id'])] = task
            tasks['task_' + task['id']] = {
                'id_pf': task['id'],
                'id_pf_general': task['general'],
                'name': task['title'],
                'description': task['description'],
                'project_id': dict_key('pr_' + task['statusSet'], processes4flectra),
                'stage_id': dict_key('st_' + task['status'], statuses4flectra),
                'create_date': str(task['beginDateTime']).replace('-', '.') + ':00',
                'user_id': 'users_pf.user_' + chk_users(task['owner']['id']),
                'employee_id':  'hr_pf.empl_' + chk_users(task['owner']['id']),
                'tasktemplate_id': dict_key('tt_' + task['template']['id'], tasktemplates4flectra),
            }
            if task.get('importance', None):
                if task['importance'] == 'HIGH':
                    tasks['task_' + task['id']]['priority'] = '0'
                else:
                    tasks['task_' + task['id']]['priority'] = '2'
            else:
                tasks['task_' + task['id']]['priority'] = '2'
            if task.get('startTime', None):
                if len(str(task['startTime'])) < 16:
                    tasks['task_' + task['id']]['date_start'] = \
                        str(task['startTime']).strip(' ')[:10].replace('-', '.') + ' 09:00:00'
                else:
                    tasks['task_' + task['id']]['date_start'] = str(task['startTime']).replace('-', '.') + ':00'
            if task.get('endTime', None):
                if len(str(task['endTime'])) < 16:
                    tasks['task_' + task['id']]['date_deadline'] = \
                        str(task['endTime']).strip(' ')[:10].replace('-', '.') + ' 09:00:00'
                else:
                    tasks['task_' + task['id']]['date_deadline'] = str(task['endTime']).replace('-', '.') + ':00'
            if task.get('duration', None) and task.get('durationUnit', None):
                if task['durationUnit'] == 0:
                    tasks['task_' + task['id']]['planned_hours'] = str(int(task['duration'])*60)
                elif task['durationUnit'] == 1:
                    tasks['task_' + task['id']]['planned_hours'] = task['duration']
                elif task['durationUnit'] == 2:
                    tasks['task_' + task['id']]['planned_hours'] = str(int(task['duration'])/24)

    for task in tasks_from_json:
        if task['type'] == 'task':
            down_recursion = True
            project_ids = [int(task['id'])]
            current_id = task['id']
            while down_recursion:
                parent_id = check_parent_id(current_id, tasks_from_json_dict)
                if parent_id:
                    tasks['task_' + task['id']]['parent_id'] = 'task_' + str(parent_id)
                    project_ids.append(parent_id)
                    current_id = parent_id
                else:
                    down_recursion = False
            project_ids.sort()
            for task_id in project_ids:
                tasks['task_' + str(task_id)]['project_id'] = tasks['task_' + str(project_ids[0])]['project_id']
            if task.get('customData', None):
                if task['customData'].get('customValue', None):
                    if str(type(task['customData']['customValue'])).find('list') > -1:
                        for field in task['customData']['customValue']:
                            if not template_fields.get('tpl_field_' + field['field']['id']):
                                template_fields['tpl_field_' + field['field']['id']] = {
                                    'name': field['field']['name'],
                                    'id_pf': field['field']['id']
                                }
                    else:
                        field = task['customData']['customValue']
                        if not template_fields.get('tpl_field_' + field['field']['id']):
                            template_fields['tpl_field_' + field['field']['id']] = {
                                'name': field['field']['name'],
                                'id_pf': field['field']['id']
                            }
    for task in tasks_from_json:
        if task['type'] == 'task':
            if task.get('customData', None):
                if task['customData'].get('customValue', None):
                    if str(type(task['customData']['customValue'])).find('list') > -1:
                        for field in task['customData']['customValue']:
                            fields_fills[task['id'] + '_' + field['field']['id']] = {
                                'task_id': dict_key('task_' +  task['id'], tasks),
                                'template_field_name_id': dict_key('tpl_field_' + field['field']['id'], template_fields),
                                'text': field.get('text',''),
                                'value': field.get('value',''),
                            }
                    else:
                        field = task['customData']['customValue']
                        fields_fills[task['id'] + '_' + field['field']['id']] = {
                            'task_id': 'task_' + task['id'],
                            'template_field_name_id': 'tpl_field_' + field['field']['id'],
                            'text': field.get('text', ''),
                            'value': field.get('value', ''),
                        }

    # Заголовок xml
    flectra_root = objectify.Element('flectra')
    flectra_data = objectify.SubElement(flectra_root, 'data')

    # Процессы (project.project)
    for process in processes4flectra:
        record = create_record(process, 'project.project', processes4flectra[process])
        flectra_data.append(record)

    # Статусы (project.task.type)
    for status in statuses4flectra:
        record = create_record(status, 'project.task.type', statuses4flectra[status])
        flectra_data.append(record)

    # Шаблоны полей (docflow.field.template)
    for template_field in template_fields:
        record = create_record(str(template_field), 'docflow.field.template', template_fields[template_field])
        flectra_data.append(record)

    # Шаблоны задач (docflow.tasktemplate)
    for tasktemplate in tasktemplates4flectra:
        record = create_record(tasktemplate, 'docflow.tasktemplate', tasktemplates4flectra[tasktemplate])
        flectra_data.append(record)

    # Задачи (project.task)
    for i in range(min(tasks_full.keys())-10,max(tasks_full.keys())+10):
        if tasks.get('task_' + str(i), None):
            record = create_record('task_' + str(i), 'project.task', tasks['task_' + str(i)])
            flectra_data.append(record)

    # Поля (docflow.field)
    for field_fill in fields_fills:
        record = create_record(field_fill, 'docflow.field', fields_fills[field_fill])
        flectra_data.append(record)

    # Комментарии
    # Загружаем бэкап комментариев
    actions4flectra = {}
    actions = {}
    with open(os.path.join(PF_BACKUP_DIRECTORY, 'actions_full.json'), 'r') as read_file:
        actions_str = json.load(read_file)
    for action in actions_str:
        actions[int(action)] = actions_str[action]
    print('Из сохраненных комментариев:', len(actions))

    # Формируем комментарии для вывода в Flectra
    for action in actions:
        if int(actions[action]['task']['id']) in tasks_from_json_ids:
            actions4flectra['msg_' + str(actions[action]['id'])] = {
                'date': actions[action]['dateTime'] + ':00',
                'author_id': 'users_pf.user_' + chk_users(actions[action]['owner']['id']) + '_res_partner',
                'res_id': 'task_' + str(actions[action]['task']['id']),
                'body': actions[action]['description'],
                'message_type': 'comment',
                'model': 'project.task'
            }
    for action in actions4flectra:
        record = create_record(action, 'mail.message', actions4flectra[action])
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



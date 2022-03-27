# Загружаем задачи, комментарии и сопутствующую информацию из АПИ ПФ

import json
import os
import requests
import xmltodict
from lxml import etree, objectify
import csv

from lib import format_phone, l
from hide_data import URL, USR_Tocken, PSR_Tocken, PF_ACCOUNT

PF_BACKUP_DIRECTORY = '../../hr_pf/get_pf/planfix-data-202203271752'
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

def load_statuses_from_api():
    """ Загружаем список процессов и список статусов по каждому процессу """
    processes = {}
    statuses = {}
    inactive = set()
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
            'id_pf': process['id'],
            'ExternalID': 'pr_'+ str(process['id'])
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
            if status['isActive'] == '0':
                inactive.add(status['id'])
            if statuses.get('st_' + status['id'], None):
                statuses['st_' + status['id']]['project_ids'] += ['pr_' + process['id']]
            else:
                statuses['st_' + status['id']] = {
                    'name': status['name'],
                    'id_pf': status['id'],
                    'project_ids': ['pr_' + process['id']],
                    'ExternalID': 'st_'+ str(status['id'])
            }
    return processes, statuses, inactive


def load_tasks_templates_from_api():
    """ Загружаем шаблоны задач """
    tasktemplates = {}
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
                tasktemplates['tt_' + template['id']] = {
                    'name': template['title'],
                    'id_pf':  template['id'],
                    'id_pf_general': template['general']
                }
        i += 1
    return tasktemplates


def load_all_tasks_from_api():
    """ Загружаем все задачи из АПИ"""
    return

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


if __name__ == "__main__":
    # Загружаем бэкап комментариев
    #with open(os.path.join(PF_BACKUP_DIRECTORY, 'actions.json'), 'r') as read_file:
    #    actions_from_json = json.load(read_file)

    # id загруженных в модуле hr_pf юзеров и сотрудников
    users = {}
    employees = {}
    with open(os.path.join(PF_DATA_DIRECTORY, 'users.csv'), 'r') as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            if l(row['id_pf']) > 0:
                users[int(row['id_pf'])] = 'hr_pf.user_' + str(row['id_pf'])
                employees[int(row['id_pf'])] = 'hr_pf.empl_' + str(row['id_pf'])
                if l(row['userid_pf']) > 0:
                    users[int(row['userid_pf'])] = 'hr_pf.user_' + str(row['id_pf'])
                    employees[int(row['userid_pf'])] = 'hr_pf.empl_' + str(row['id_pf'])

    # Загружаем бэкап задач из стандартного полного бэкапа ПФ
    tasks_from_pf_backup_dict = {}
    inactive_tasks_ids = set()
    all_tasks_ids = set()
    with open(os.path.join(PF_BACKUP_DIRECTORY, 'tasks.json'), 'r') as read_file:
        tasks_from_pf_backup = json.load(read_file)
    for task in tasks_from_pf_backup:
        tasks_from_pf_backup_dict[int(task['id'])] = task
        all_tasks_ids.add(int(task['id']))

    # Загружаем бэкап задач из выгрузки всех задач (task.getMulti) через АПИ ПФ
    tasks_full_from_api_backup_dict = {}
    with open(os.path.join(PF_BACKUP_DIRECTORY, 'tasks_full.json'), 'r') as read_file:
        tasks_full_from_api_backup = json.load(read_file)
    for task in tasks_full_from_api_backup:
        tasks_full_from_api_backup_dict[int(task['id'])] = task
        all_tasks_ids.add(int(task['id']))
    tasks_full_from_api_backup = list(tasks_full_from_api_backup_dict.values())
    print('Из сохраненных полных (task.getMulti):', len(tasks_full_from_api_backup))

    # Загружаем бэкап задач из выгрузки списка задач (task.getList) через АПИ ПФ
    tasks_short_dict = {}
    with open(os.path.join(PF_BACKUP_DIRECTORY, 'tasks_short.json'), 'r') as read_file:
        tasks_short = json.load(read_file)
    for task in tasks_short:
        tasks_short_dict[int(task['id'])] = task
        all_tasks_ids.add(int(task['id']))
    tasks_short = list(tasks_short_dict.values())
    print('Из сохраненной выгрузки списка:', len(tasks_short))

    if RELOAD_ALL_FROM_API:
        # Загружаем обновление для всех активных задач
        i = 1
        tasks_short = []
        printProgressBar(0, len(tasks_from_pf_backup_dict), prefix='Скачано:', suffix='задач', length=50)
        try:
            while True:
                answer = requests.post(
                    URL,
                    headers=PF_HEADER,
                    data='<request method="task.getList"><account>' + PF_ACCOUNT +
                         '</account><target>all</target><pageSize>100</pageSize><pageCurrent>' + str(i) +
                         '</pageCurrent></request>',
                    auth=(USR_Tocken, PSR_Tocken)
                )
                if answer.text.find('count="0"/></response>') > -1:
                    break
                else:
                    tasks_short += xmltodict.parse(answer.text)['response']['tasks']['task']
                printProgressBar(len(tasks_short), len(tasks_from_pf_backup_dict), prefix='Скачано:', suffix='задач',
                                 length=50)
                i += 1
        finally:
            tasks_short_dict = {}
            for task in tasks_short:
                tasks_short_dict[int(task['id'])] = task
                all_tasks_ids.add(int(task['id']))
            with open(os.path.join(PF_BACKUP_DIRECTORY, 'tasks_short.json'), 'w') as write_file:
                    json.dump(list(tasks_short_dict.values()), write_file, ensure_ascii=False)
            print('Загружено ', len(tasks_short_dict), 'коротких задач')

    # Догружаем найденные задачи в полный бэкап tasks_full_from_api_backup
    tasks_all = tasks_full_from_api_backup
    hundred4xml = []
    hundred_ids = []
    all_ids = []
    printProgressBar(0, len(tasks_from_pf_backup), prefix='Скачано:', suffix='задач', length=50)
    try:
        for task in all_tasks_ids:
            if not tasks_full_from_api_backup_dict.get(task, None):
                hundred_ids += [int(task)]
                hundred4xml += ['<id>' + str(task) + '</id>']
                if len(hundred4xml) > 99:
                    answer = requests.post(URL, headers=PF_HEADER,
                        data='<request method="task.getMulti"><account>' + PF_ACCOUNT +
                             '</account><tasks>' + ''.join(hundred4xml) + '</tasks></request>',
                        auth=(USR_Tocken, PSR_Tocken)
                    )
                    i = 0
                    while not answer.ok:
                        answer = requests.post(
                            URL,
                            headers=PF_HEADER,
                            data='<request method="task.getMulti"><account>' + PF_ACCOUNT +
                                 '</account><tasks>' + ''.join(hundred4xml) + '</tasks></request>',
                            auth=(USR_Tocken, PSR_Tocken))
                        if i > 10:
                            break
                        i += 1
                    if xmltodict.parse(answer.text)['response'].get('tasks', None):
                        if xmltodict.parse(answer.text)['response']['tasks'].get('task', None):
                            loaded_tasks = xmltodict.parse(answer.text)['response']['tasks']['task']
                            if str(type(loaded_tasks)).find('list') > -1:
                                for loaded_task in loaded_tasks:
                                    if l(loaded_task['id']) not in hundred_ids:
                                        print('Скачалось не то:', loaded_task['id'])
                                tasks_all += xmltodict.parse(answer.text)['response']['tasks']['task']
                            else:
                                if l(loaded_tasks['id']) not in hundred_ids:
                                    print('Скачалось не то:', loaded_tasks['id'])
                                tasks_all += [xmltodict.parse(answer.text)['response']['tasks']['task']]
                        else:
                            pass
                            #print('Вообще не загрузилось:\n', ''.join(hundred4xml))
                    else:
                        pass
                        #print('Не загрузилось:\n', ''.join(hundred4xml))
                    hundred4xml = []
                    all_ids += hundred_ids
                    hundred_ids = []
                    if os.path.exists(os.path.join(PF_BACKUP_DIRECTORY, 'tasks_full_stop')):
                        raise ValueError
                    printProgressBar(len(tasks_all), len(tasks_from_pf_backup_dict), prefix='Скачано:', suffix='задач', length=50)
    finally:
        tasks_all_dict = {}
        for task in tasks_all:
            tasks_all_dict[int(task['id'])] = task
        print('Загружено:', len(tasks_all), 'Сохранено:', len(tasks_all_dict), 'Новых:', len(all_ids))
        if RELOAD_ALL_FROM_API:
            for task in tasks_all_dict:             # Обновляем во всех задачах информацию из tasks_short_dict
                if tasks_short_dict.get(task, None):
                    for task_property in tasks_short_dict[task]:
                        tasks_all_dict[task][task_property] = tasks_short_dict[task][task_property]
        if RELOAD_ALL_FROM_API: #or all_ids:
            with open(os.path.join(PF_BACKUP_DIRECTORY, 'tasks_full.json'), 'w') as write_file:
                    json.dump(list(tasks_all_dict.values()), write_file, ensure_ascii=False)

    # Загружаем список процессов и статусов из АПИ
    processes, statuses, inactive_statuses = load_statuses_from_api()
    inactive_statuses.add('211')   # Шаблон сформирован
    inactive_statuses.add('210')   # Договор заключен
    inactive_statuses.add('5')  # Отклоненная
    inactive_statuses.add('249') # НЕ согласовано
    inactive_statuses.add('143')  # Заявка исполнена
    inactive_statuses.add('147')  # Заявка отменена/отклонена
    inactive_statuses.remove('4')  # Отложенная

    # Загружаем шаблоны задач из АПИ
    tasktemplates = load_tasks_templates_from_api()

    # Загружаем данные по задачам из файла, полученного из АПИ
    tasks_from_json = list(tasks_all_dict.values()) #[40000:40400]

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
                'project_id': dict_key('pr_' + task['statusSet'], processes),
                'stage_id': dict_key('st_' + task['status'], statuses),
                'create_date': str(task['beginDateTime']).replace('-', '.') + ':00',
                'user_id': users.get(task['owner']['id'], ''),
                'employee_id':  employees.get(task['owner']['id'], ''),
                'tasktemplate_id': dict_key('tt_' + task['template']['id'], tasktemplates),
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
            if task.get('parent', None):
                if task['parent'].get('id', None) and tasks_from_json_dict.get(int(task['parent']['id']), None):
                    if task['id'] > task['parent']['id']:
                        tasks['task_' + task['id']]['parent_id'] = 'task_' + task['parent']['id']
                        tasks['task_' + task['id']]['project_id'] = tasks['task_' + task['parent']['id']]['project_id']
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
    for process in processes:
        record = create_record(process, 'project.project', processes[process])
        flectra_data.append(record)

    # Статусы
    for status in statuses:
        record = create_record(status, 'project.task.type', statuses[status])
        flectra_data.append(record)

    # Шаблоны полей
    for template_field in template_fields:
        record = create_record(str(template_field), 'docflow.field.template', template_fields[template_field])
        flectra_data.append(record)

    # Шаблоны задач
    for tasktemplate in tasktemplates:
        record = create_record(tasktemplate, 'docflow.tasktemplate', tasktemplates[tasktemplate])
        flectra_data.append(record)

    # Задачи (project.project)
    for i in range(min(tasks_all_dict.keys())-10,max(tasks_all_dict.keys())+10):
        if tasks.get('task_' + str(i), None):
            record = create_record('task_' + str(i), 'project.task', tasks['task_' + str(i)])
            flectra_data.append(record)

    # Поля
    for field_fill in fields_fills:
        record = create_record(field_fill, 'docflow.field', fields_fills[field_fill])
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

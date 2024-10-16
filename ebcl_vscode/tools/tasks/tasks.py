#!/usr/bin/env python
""" Generate VS Code build tasks. """
import argparse
import json
import logging
import os

from typing import Optional, Any

import yaml

from ebcl.common import init_logging, bug, promo


class TaskGenerator:
    """ Generate VS Code build tasks.  """

    # TODO: test

    tasks: Optional[dict[str, Any]]

    def __init__(self, config: Optional[str] = None):
        """ Load task configuration from config file. """
        self.tasks = None

        file = os.path.join(os.path.dirname(__file__), 'tasks.yaml')

        if config:
            file = os.path.join(config)

        logging.info('Using task config %s...', file)

        with open(file, encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        logging.debug('Config: %s', self.config)

    def load_tasks(self, template: Optional[str] = None):
        """ Load the base tasks.json file. """
        file = os.path.join(os.path.dirname(__file__), 'tasks.json')

        if template:
            workspace = self.config.get('workspace', '/workspace')
            file = os.path.join(workspace, template)

        logging.info('Using tasks.json template %s...', file)

        with open(file, 'r', encoding='utf-8') as tasks_file:
            self.tasks = json.load(tasks_file)

    def _add_task(self, name: str, cwd: str, command: str,
                  description: str, args: list[str]) -> None:
        """ Add a task to the tasks list. """

        logging.debug('Adding task %s with command %s %s...',
                      name, command, args)

        task: dict[str, Any] = dict()
        task['type'] = 'shell'
        task['label'] = f'EBcL: {name}'
        task['command'] = command
        task['args'] = args
        task['group'] = {
            'kind': 'build',
            'isDefault': True
        }
        task['options'] = {
            'cwd': cwd
        }
        task['detail'] = description

        assert self.tasks

        self.tasks['tasks'].append(task)

    def _is_ignored(self, path: str) -> bool:
        """ Test if file is ignored. """
        ignore = self.config.get('ignore', [])

        for ign in ignore:
            if ign in path:
                logging.debug('Path %s is ignored. (%s)...',
                              path, ignore)
                return True

        return False

    def generate_image_tasks(self):
        """ Generate build tasks for all images and sysroots. """
        assert self.config

        workspace = self.config.get('workspace', '/workspace')
        folders = self.config.get('folders', [])

        logging.info('Generating tasks (w: %s, f: %s)...',
                     workspace, folders)

        for folder in folders:
            folder = os.path.abspath(os.path.join(workspace, folder))

            logging.info('Processing folder %s...', folder)

            if not os.path.isdir(folder):
                logging.error('Image folder %s not found!', folder)
                continue

            for root, _dir, files in os.walk(folder):
                if self._is_ignored(root):
                    logging.debug('Folder %s is ignored.', root)
                    continue

                for file in files:
                    if file != 'Makefile':
                        continue

                    file = os.path.join(root, file)

                    if self._is_ignored(file):
                        logging.info('File %s is ignored.', file)
                        continue

                    logging.debug('Processing file %s...', file)

                    name = os.path.relpath(root, folder)

                    tasks = [
                        {
                            'name': f'Image {name}',
                            'desc': f'Run the image build for {name}',
                            'args': ['image']
                        },
                        {
                            'name': f'Sysroot {name}',
                            'desc': f'Build and install the sysroot for {name}',
                            'args': ['sysroot_install']
                        }
                    ]

                    if '/qemu/' in file:
                        tasks.append({
                            'name': f'QEMU {name}',
                            'desc': f'Run {name} in QEMU'
                        })

                    logging.debug('Adding tasks %s...', tasks)

                    for task in tasks:
                        self._add_task(
                            name=str(task['name']),
                            cwd=str(root),
                            args=list(task.get('args', [])),
                            command='make',
                            description=str(task['desc'])
                        )

    def save_tasks(self, output: Optional[str] = None):
        """ Update VS Code tasks file. """
        out = '.vscode/tasks.json'
        if output:
            out = output

        workspace = self.config.get('workspace', '/workspace')
        file = os.path.join(workspace, out)

        logging.info('Writing tasks.json to %s.', file)

        with open(file, 'w', encoding='utf-8') as tasks_file:
            json.dump(self.tasks, tasks_file, indent=4)

    def genenrate_tasks(
            self,
            output: Optional[str] = None,
            template: Optional[str] = None
    ):
        """ Generate tasks.json. """

        logging.info('Generating tasks (o: %s, t: %s)...', output, template)

        self.load_tasks(template=template)
        self.generate_image_tasks()
        self.save_tasks(output=output)


def main() -> None:
    """ Main entrypoint of EBcL VS Code task generator. """
    init_logging()

    parser = argparse.ArgumentParser(
        description='Generate VS Code build task for images.')
    parser.add_argument('-c', '--config', type=str,
                        help='Path to the YAML configuration file.')
    parser.add_argument('-o', '--output', type=str,
                        help='Path to the output directory')
    parser.add_argument('-t', '--template', type=str,
                        help='Template for tasks.json.')

    args = parser.parse_args()

    generator = TaskGenerator(args.config)

    try:
        generator.genenrate_tasks()
    except Exception as e:
        logging.critical('VS Code build task generation failed! %s', e)
        bug(bug_url='https://github.com/Elektrobit/ebcl_vscode_tools/issues')
        exit(1)

    promo()


if __name__ == '__main__':
    main()

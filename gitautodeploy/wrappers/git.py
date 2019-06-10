# -*- coding: utf-8 -*-


class GitWrapper:
    """Wraps the git client. Currently uses git through shell command
    invocations."""

    def __init__(self):
        pass

    @staticmethod
    def init(repo_config):
        """Init remote url of the repo from the git server"""
        import logging
        from .process import ProcessWrapper
        import os

        logger = logging.getLogger()
        logger.info("Initializing repository %s" % repo_config['path'])

        commands = []

        commands.append('unset GIT_DIR')
        commands.append('git remote set-url ' + repo_config['remote'] + " " + repo_config['url'])
        commands.append('git fetch ' + repo_config['remote'])
        commands.append('git checkout -f -B ' + repo_config['branch'] + ' -t ' + repo_config['remote'] + '/' + repo_config['branch'])
        commands.append('git submodule update --init --recursive')

        # All commands need to success
        cmd_res = []
        for command in commands:
            res = ProcessWrapper().call(command, cwd=repo_config['path'], shell=True, supressStderr=True)
            cmd_res.append(res)

            if res != 0:
                logger.error("Command '%s' failed with exit code %s" % (command, res))
                break

        if all(res == 0 for res in cmd_res) and os.path.isdir(repo_config['path']):
            logger.info("Repository %s successfully initialized" % repo_config['path'])
        else:
            logger.error("Unable to init repository %s" % repo_config['path'])

    @staticmethod
    def pull(repo_config, event):
        """Pulls the latest version of the repo from the git server"""
        import logging
        from .process import ProcessWrapper
        import os

        logger = logging.getLogger()

        logger.info("Updating repository %s" % repo_config['path'])

        # Only pull if there is actually a local copy of the repository
        if 'path' not in repo_config:
            logger.info('No local repository path configured, no pull will occure')
            return 0

        commands = []

        commands.append('unset GIT_DIR')

        if "prepull" in repo_config:
            commands.append(repo_config['prepull'])

        commands.append('git fetch ' + repo_config['remote'])
        commands.append('git reset --hard ' + repo_config['remote'] + "/" + repo_config['branch'])
        commands.append('git submodule update --init --recursive')

        if "postpull" in repo_config:
            commands.append(repo_config['postpull'])

        # All commands need to success
        cmd_res = []
        for command in commands:
            res = ProcessWrapper().call(command, cwd=repo_config['path'], shell=True, supressStderr=True)
            cmd_res.append(res)

            if res != 0:
                logger.error("Command '%s' failed with exit code %s" % (command, res))
                break

        if all(res == 0 for res in cmd_res) and os.path.isdir(repo_config['path']):
            event.log_info(u"Código atualizado com \"%s\"" % repo_config['remote'])
            return True
        else:
            event.log_error(u"Não foi possível atualizar o código com \"%s\"" % repo_config['remote'])
            return False

    @staticmethod
    def clone(repo_config):
        """Clones the latest version of the repo from the git server"""
        import logging
        from .process import ProcessWrapper
        import os

        logger = logging.getLogger()

        logger.info("Cloning repository %s" % repo_config['path'])

        # Only pull if there is actually a local copy of the repository
        if 'path' not in repo_config:
            logger.info('No local repository path configured, no clone will occure')
            return 0

        commands = []

        commands.append('unset GIT_DIR')
        commands.append('git clone --recursive ' + repo_config['url'] + ' -b ' + repo_config['branch'] + ' ' + repo_config['path'])

        # All commands need to success
        cmd_res = []
        for command in commands:
            res = ProcessWrapper().call(command, shell=True)
            cmd_res.append(res)

            if res != 0:
                logger.error("Command '%s' failed with exit code %s" % (command, res))
                break

        if all(res == 0 for res in cmd_res) and os.path.isdir(repo_config['path']):
            logger.info("Repository %s successfully cloned" % repo_config['url'])
        else:
            logger.error("Unable to clone repository %s" % repo_config['url'])

    @staticmethod
    def deploy(repo_config, event):
        """Executes any supplied post-pull deploy command"""
        from .process import ProcessWrapper
        import logging
        logger = logging.getLogger()

        if not 'deploy_commands' in repo_config or len(repo_config['deploy_commands']) == 0:
            logger.info('No deploy commands configured')
            return []

        logger.info('Executing deploy commands')

        # Use repository path as default cwd when executing deploy commands
        cwd = (repo_config['path'] if 'path' in repo_config else None)

        for cmd in repo_config['deploy_commands']:
            if isinstance(cmd, basestring):
                res = ProcessWrapper().call([cmd], cwd=cwd, shell=True)

                if res == 0:
                    event.log_info(u"Comando \"%s\" executado" % cmd)
                else:
                    event.log_error(u"Comando \"%s\" falhou" % cmd)
            else:
                for cmd_name, cmd_value in cmd.items():
                    res = ProcessWrapper().call([cmd_value], cwd=cwd, shell=True)

                    if res == 0:
                        event.log_info(u"%s" % cmd_name)
                    else:
                        event.log_error(u"%s falhou" % cmd_name)

    @staticmethod
    def copy(repo_config, event):
        """Copy from base directory"""
        import logging
        from .process import ProcessWrapper
        import os

        logger = logging.getLogger()

        logger.info("Copy branch %s" % repo_config['branch'])

        if 'base' not in repo_config:
            logger.info('No base configured, no copy will occure')
            return 0

        if 'path' not in repo_config:
            logger.info('No path configured, no copy will occure')
            return 0

        if 'branch' not in repo_config:
            logger.info('No branch configured, no copy will occure')
            return 0

        commands = []
        rewrite = False

        if os.path.isdir(repo_config['path']):
            commands.append('rm -rf %s' % repo_config['path'])
            rewrite = True

        commands.append('cp -rf %s %s' % (repo_config['base'], repo_config['path']))

        # All commands need to success
        cmd_res = []
        for command in commands:
            res = ProcessWrapper().call(command, shell=True)
            cmd_res.append(res)

            if res != 0:
                logger.error("Command '%s' failed with exit code %s" % (command, res))
                break

        if all(res == 0 for res in cmd_res) and os.path.isdir(repo_config['path']):
            event.log_info(u"Ambiente \"%s\" %s" % (repo_config['branch'], "recriado" if rewrite else "criado"))
        else:
            event.log_error(u"Não foi possível criar o ambiente \"%s\"" % repo_config['branch'])

    @staticmethod
    def destroy(repo_config, event):
        import logging
        from .process import ProcessWrapper
        import os

        logger = logging.getLogger()

        logger.info("Destroy branch %s dir" % repo_config['branch'])

        if 'path' not in repo_config:
            logger.info('No path configured, no destroy will occure')
            return 0

        if 'branch' not in repo_config:
            logger.info('No branch configured, no destroy will occure')
            return 0

        commands = []

        commands.append('rm -rf %s' % repo_config['path'])

        # All commands need to success
        cmd_res = []
        for command in commands:
            res = ProcessWrapper().call(command, shell=True)
            cmd_res.append(res)

            if res != 0:
                logger.error("Command '%s' failed with exit code %s" % (command, res))
                break

        if all(res == 0 for res in cmd_res) and not os.path.isdir(repo_config['path']):
            event.log_info(u"Ambiente \"%s\" destruído" % repo_config['branch'])
        else:
            event.log_error(u"Não foi possível destruir o ambiente \"%s\"" % repo_config['branch'])

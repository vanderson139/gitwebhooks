# -*- coding: utf-8 -*-

from __future__ import absolute_import
from .events import WebhookAction
from .parsers import get_service_handler


def WebhookRequestHandlerFactory(config, event_store, server_status, is_https=False):
    """Factory method for webhook request handler class"""
    try:
        from SimpleHTTPServer import SimpleHTTPRequestHandler
    except ImportError as e:
        from http.server import SimpleHTTPRequestHandler

    class WebhookRequestHandler(SimpleHTTPRequestHandler, object):
        """Extends the BaseHTTPRequestHandler class and handles the incoming
        HTTP requests."""

        def __init__(self, *args, **kwargs):
            self._config = config
            self._event_store = event_store
            self._server_status = server_status
            self._is_https = is_https
            super(WebhookRequestHandler, self).__init__(*args, **kwargs)

        def end_headers(self):
            self.send_header('Access-Control-Allow-Origin', '*')
            SimpleHTTPRequestHandler.end_headers(self)

        def do_HEAD(self):

            # Web UI needs to be enabled
            if not self.validate_web_ui_enabled():
                return

            # Web UI might require HTTPS
            if not self.validate_web_ui_https():
                return

            # Client needs to be whitelisted
            if not self.validate_web_ui_whitelist():
                return

            # Client needs to authenticate
            if not self.validate_web_ui_basic_auth():
                return

            return SimpleHTTPRequestHandler.do_HEAD(self)

        def do_GET(self):

            # Web UI needs to be enabled
            if not self.validate_web_ui_enabled():
                return

            # Web UI might require HTTPS
            if not self.validate_web_ui_https():
                return

            # Client needs to be whitelisted
            if not self.validate_web_ui_whitelist():
                return

            # Client needs to authenticate
            if not self.validate_web_ui_basic_auth():
                return

            # Handle status API call
            if self.path == "/api/status":
                self.handle_status_api()
                return

            if self.path == "/api/dynamic-envs":
                self.handle_dynamic_envs()
                return

            # Serve static file
            return SimpleHTTPRequestHandler.do_GET(self)

        def handle_status_api(self):
            import json

            data = {
                'events': self._event_store.dict_repr(),
                'auth-key': self._server_status['auth-key']
            }

            data.update(self.get_server_status())

            self.send_response(200, 'OK')
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode('utf-8'))

        def handle_dynamic_envs(self):
            import json
            import os

            data = []
            repositories = []

            for repository in self._config['repositories']:

                if repository['dynamic'] and 'review' in repository:
                    repository_name = repository['url'].split('/')[-1].split('.git')[0]

                    if repository_name not in repositories:

                        dynamic_envs_path = os.path.expanduser(repository['review']['path'])
                        envs = []

                        if os.path.isdir(dynamic_envs_path):
                            for name in os.listdir(dynamic_envs_path):
                                if os.path.isdir(os.path.join(dynamic_envs_path, name)):
                                    envs.append(name)

                        data.append({
                            'repository': repository_name,
                            'envs': envs
                        })

                        repositories.append(repository_name)

            self.send_response(200, 'OK')
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode('utf-8'))

        def do_POST(self):
            """Invoked on incoming POST requests"""
            from threading import Timer
            import logging
            import json
            import threading
            import time
            from urlparse import parse_qs

            logger = logging.getLogger()

            content_length = int(self.headers.get('content-length'))
            request_body = self.rfile.read(content_length).decode('utf-8')

            # Extract request headers and make all keys to lowercase (makes them easier to compare)
            request_headers = dict(self.headers)
            request_headers = dict((k.lower(), v) for k, v in request_headers.items())

            # Payloads from GitHub can be delivered as form data. Test the request for this pattern and extract json payload
            if request_headers['content-type'] == 'application/x-www-form-urlencoded':
                res = parse_qs(request_body.decode('utf-8'))
                if 'payload' in res and len(res['payload']) == 1:
                    request_body = res['payload'][0]

            # Payload need be json
            try:
                json.loads(request_body)
            except ValueError:
                self.send_error(400, 'Bad request')
                return

            action = WebhookAction(self.client_address, request_headers, request_body)
            self._event_store.register_action(action)
            action.set_waiting(True)

            action.log_info(u"Requisição de %s:%s" % (self.client_address[0], self.client_address[1]))

            # Test case debug data
            test_case = {
                'headers': dict(self.headers),
                'payload': json.loads(request_body),
                'config': {},
                'expected': {'status': 200, 'data': [{'deploy': 0}]}
            }

            try:

                # Will raise a ValueError exception if it fails
                ServiceRequestHandler = get_service_handler(request_headers, request_body, action)

                # Unable to identify the source of the request
                if not ServiceRequestHandler:
                    self.send_error(400, 'Unrecognized service')
                    test_case['expected']['status'] = 400
                    action.log_error("O serviço de origem não é suportado")
                    action.set_waiting(False)
                    action.set_success(False)
                    return

                service_handler = ServiceRequestHandler(self._config)

                action.log_debug(u"Manipulando a requisição com %s" % ServiceRequestHandler.__name__)

                # Could be GitHubParser, GitLabParser or other
                projects = service_handler.get_matching_projects(request_headers, request_body, action)

                # Charm
                time.sleep(0.5)

                action.log_info(u"%s candidat%s correspond%s a requisição" %
                                (len(projects), 'o' if len(projects) is 1 else 'os',
                                 'e' if len(projects) is 1 else 'em'))

                # request_filter = WebhookRequestFilter()

                if len(projects) == 0:
                    self.send_error(400, 'Bad request')
                    test_case['expected']['status'] = 400
                    action.log_error(u"Nenhum projeto correspondente")
                    action.set_waiting(False)
                    action.set_success(False)
                    return

                # Apply filters
                matching_projects = []
                for project in projects:
                    if project.apply_filters(request_headers, request_body, action):
                        matching_projects.append(project)

                # Only keep projects that matches
                projects = matching_projects

                # Charm
                time.sleep(0.5)

                log_message = u"%s candidat%s correspond%s após filtros" %\
                              (len(projects), 'o' if len(projects) is 1 else 'os',
                               'e' if len(projects) is 1 else 'em')

                if len(projects) == 0:
                    action.log_warning(log_message)
                else:
                    action.log_info(log_message)

                if not service_handler.validate_request(request_headers, request_body, projects, action):
                    self.send_error(400, 'Bad request')
                    test_case['expected']['status'] = 400
                    action.log_error(u"A solicitação foi rejeitada, o token de segurança é incompatível")
                    action.set_waiting(False)
                    action.set_success(False)
                    return

                test_case['expected']['status'] = 200

                self.send_response(200, 'OK')
                self.send_header('Content-type', 'text/plain')
                self.end_headers()

                if len(projects) == 0:
                    action.set_waiting(False)
                    action.set_success(False)
                    return

                # Charm
                time.sleep(0.5)

                action.log_info(u"Prosseguindo com %s deplo%s" %
                                (len(projects), 'y' if len(projects) is 1 else 'ys'))
                action.set_waiting(False)
                action.set_success(True)

                for project in projects:

                    # Schedule the execution of the webhook (git pull and trigger deploy etc)
                    thread = threading.Thread(target=project.execute_webhook, args=[self._event_store])
                    thread.start()

                    # Add additional test case data
                    test_case['config'] = {
                        'url': 'url' in project and project['url'],
                        'branch': 'branch' in project and project['branch'],
                        'remote': 'remote' in project and project['remote'],
                        'deploy': 'echo test!'
                    }

            except ValueError as e:
                self.send_error(400, 'Unprocessable request')
                action.log_error(u"Não foi possível processar a requisição de %s:%s" % (self.client_address[0], self.client_address[1]))
                test_case['expected']['status'] = 400
                action.set_waiting(False)
                action.set_success(False)
                return

            except Exception as e:
                self.send_error(500, 'Unable to process request')
                test_case['expected']['status'] = 500
                action.log_error(u"Não foi possível processar a requisição")
                action.set_waiting(False)
                action.set_success(False)

                raise e

            finally:

                # Save the request as a test case
                if 'log-test-case' in self._config and self._config['log-test-case']:
                    self.save_test_case(test_case)

        def log_message(self, format, *args):
            """Overloads the default message logging method to allow messages to
            go through our custom logger instead."""
            import logging
            logger = logging.getLogger()
            logger.info("%s - %s" % (self.client_address[0], format%args))

        def save_test_case(self, test_case):
            """Log request information in a way it can be used as a test case."""
            import time
            import json
            import os

            # Mask some header values
            masked_headers = ['x-github-delivery', 'x-hub-signature']
            for key in test_case['headers']:
                if key in masked_headers:
                    test_case['headers'][key] = 'xxx'

            target = '%s-%s.tc.json' % (self.client_address[0], time.strftime("%Y%m%d%H%M%S"))
            if 'log-test-case-dir' in self._config and self._config['log-test-case-dir']:
                target = os.path.join(self._config['log-test-case-dir'], target)

            file = open(target, 'w')
            file.write(json.dumps(test_case, sort_keys=True, indent=4))
            file.close()

        def get_server_status(self):
            """Generate a copy of the server status object that contains the public IP or hostname."""

            server_status = {}
            for item in self._server_status.items():
                key, value = item
                public_host = self.headers.get('host').split(':')[0]

                if key == 'http-uri':
                    server_status[key] = value.replace(self._config['http-host'], public_host)

                if key == 'https-uri':
                    server_status[key] = value.replace(self._config['https-host'], public_host)

                if key == 'wss-uri':
                    server_status[key] = value.replace(self._config['wss-host'], public_host)

            return server_status

        def validate_web_ui_enabled(self):
            """Verify that the Web UI is enabled"""

            if self._config['web-ui-enabled']:
                return True

            self.send_error(403, "Web UI is not enabled")
            return False

        def validate_web_ui_https(self):
            """Verify that the request is made over HTTPS"""

            if self._is_https:
                return True

            if not self._config['web-ui-require-https']:
                return True

            # Attempt to redirect the request to HTTPS
            server_status = self.get_server_status()
            if 'https-uri' in server_status:
                self.send_response(307)
                self.send_header('Location', '%s%s' % (server_status['https-uri'], self.path))
                self.end_headers()
                return False

            self.send_error(403, "Web UI is only accessible through HTTPS")
            return False

        def validate_web_ui_whitelist(self):
            """Verify that the client address is whitelisted"""

            # Allow all if whitelist is empty or "*"
            if len(self._config['web-ui-whitelist']) == 0 or "*" in self._config['web-ui-whitelist']:
                return True

            # Verify that client IP is whitelisted
            if self.client_address[0] in self._config['web-ui-whitelist']:
                return True

            self.send_error(403, "%s is not allowed access" % self.client_address[0])
            return False

        def validate_web_ui_basic_auth(self):
            """Authenticate the user"""
            import base64

            if not self._config['web-ui-auth-enabled']:
                return True

            # Verify that a username and password is specified in the config
            if self._config['web-ui-username'] is None or self._config['web-ui-password'] is None:
                self.send_error(403, "Authentication credentials missing in config")
                return False

            # Verify that the provided username and password matches the ones in the config
            key = base64.b64encode("%s:%s" % (self._config['web-ui-username'], self._config['web-ui-password']))
            if self.headers.getheader('Authorization') == 'Basic ' + key:
                return True

            # Let the client know that authentication is required
            self.send_response(401)
            self.send_header('WWW-Authenticate', 'Basic realm=\"GAD\"')
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write('Not authenticated')
            return False

    return WebhookRequestHandler

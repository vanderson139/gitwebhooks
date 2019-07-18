from .base import WebhookRequestParserBase


class GitHubRequestParser(WebhookRequestParserBase):

    def get_matching_projects(self, request_headers, request_body, action):
        import json

        data = json.loads(request_body)

        repo_urls = []

        github_event = 'x-github-event' in request_headers and request_headers['x-github-event']

        action.log_info("Evento \"%s\" recebido do GitHub" % github_event)

        if 'repository' not in data:
            action.log_error("Unable to recognize data format")
            return []

        # One repository may posses multiple URLs for different protocols
        for k in ['url', 'git_url', 'clone_url', 'ssh_url']:
            if k in data['repository']:
                repo_urls.append(data['repository'][k])

        # Get a list of configured repositories that matches the incoming web hook request
        repo_configs = self.get_matching_repo_configs(repo_urls, action)

        return repo_configs

    def validate_request(self, request_headers, request_body, repo_configs, action):

        self.update_dynamic(repo_configs, request_body)

        for repo_config in repo_configs:

            # Validate secret token if present
            if 'secret-token' in repo_config and 'x-hub-signature' in request_headers:
                if not self.verify_signature(repo_config['secret-token'], request_body, request_headers['x-hub-signature']):
                    action.log_info("Request signature does not match the 'secret-token' configured for repository %s." % repo_config['url'])
                    return False

        return True

    def verify_signature(self, token, body, signature):
        import hashlib
        import hmac

        result = "sha1=" + hmac.new(str(token), body, hashlib.sha1).hexdigest()
        return result == signature

    def update_dynamic(self, repo_configs, request_body):

        for repo_config in repo_configs:

            import os
            import json

            data = json.loads(request_body)

            if repo_config['dynamic'] is True:
                head = 'refs/heads/'

                if 'ref' in data:
                    if data['ref'].startswith(head):
                        name = data['ref'][len(head):]
                    else:
                        name = data['ref']

                    repo_config['branch'] = name

                branch_path = repo_config['branch'].replace('/', '-').replace('_', '-')

                # Update path
                repo_config['path'] = os.path.expanduser("%s/%s" % (repo_config['review_path'], branch_path))
                repo_config['path_name'] = repo_config['branch']

            # Update commit
            repo_config['commit'] = {}

            if 'head_commit' in data and data['head_commit'] is not None:

                if 'message' in data['head_commit']:
                    repo_config['commit'].update({'message': data['head_commit']['message']})

                if 'id' in data['head_commit']:
                    repo_config['commit'].update({'id': data['head_commit']['id']})

                if 'compare' in data:
                    repo_config['commit'].update({'url': data['compare']})

            if 'sender' in data:
                repo_config['commit'].update({
                    'user': data['sender']['login'],
                    'user_avatar_url': data['sender']['avatar_url']
                })

        return True

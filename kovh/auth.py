from ovh import APIError


def get_current_cred(client):
    try:
        credential = client.get('/auth/currentCredential')
    except APIError:
        raise

    return credential

# TODO: clear unused code below

def has_valid_cred(client):
    try:
        cred = get_current_cred(client)
    except APIError:
        pass
    else:
        return True

    return False

def has_valid_ck(credential):
    if credential['status'] != 'validated':
        print("Credential status is '%s'" % credential['status'])
    else:
        return True

    return False

def has_sufficient_perms(credential, required_rules):
    missing_perms = []

    curr_rules = credential['rules']

    for rule in required_rules:
        if not any(r in [rule, { 'method': rule['method'], 'path': '/*'}] for r in curr_rules):
            missing_perms.append(rule)

    if len(missing_perms) > 0:
        print("Missing API permissions: %s" % missing_perms)
    else:
        return True

    return False

def need_new_ck(client, required_rules):
    credential = get_current_cred(client)

    if credential:
        if has_sufficient_perms(credential, required_rules) and has_valid_ck(credential):
            return False

    return True

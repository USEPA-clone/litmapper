from prefect.tasks.secrets import EnvVarSecret


def get_api_base_url():
    return EnvVarSecret("API_BASE_URL", raise_if_missing=True)


def get_entrez_email():
    return EnvVarSecret("ENTREZ_EMAIL", raise_if_missing=True)


def get_entrez_tool():
    return EnvVarSecret("ENTREZ_TOOL", raise_if_missing=True)


def get_entrez_api_key():
    return EnvVarSecret("ENTREZ_API_KEY", raise_if_missing=True)

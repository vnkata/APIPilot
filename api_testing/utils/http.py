
def isSuccessful(code) -> bool:
    if isinstance(code, str):
        return code[0] == '2'
    return code >= 200 and code < 300


def isInformational(code):
    return code >= 100 and code < 200


def isRedirection(code):
    return code >= 300 and code < 400


def isClientError(code):
    if isinstance(code, str):
        return code[0] == '4'
    return code >= 400 and code < 500


def isServerError(code):
    if isinstance(code, str):
        return code[0] == '5'
    return code >= 500 and code < 600

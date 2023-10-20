

def cadnum_to_id(cadnum: str) -> int:
    return int(cadnum.replace(':', '')[-8:])

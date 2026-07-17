def get_strikes(atm, direction):
    opt_type = 'PE' if direction == 'ABOVE' else 'CE'
    step = -50 if direction == 'ABOVE' else 50
    target_strikes = [atm + (i * step) for i in range(6, 0, -1)]
    return target_strikes

print('ABOVE:', get_strikes(24100, 'ABOVE'))
print('BELOW:', get_strikes(24100, 'BELOW'))

#!/usr/bin/python3

#JMP:xkovar66
import sys

import processor
from processor import Processor

import macro

SYNTAX_ERR = 55
SEMANTIC_ERR = 56
REDEF_ERR = 57
INVALID_ARG_ERR = 1
READ_FILE_ERR = 2
WRITE_FILE_ERR = 3
#
# Definice vyjimek
class InvalidArgsError(Exception): pass


class ConfigSet:
  ''' Ridici struktura, obsahuje konfiguraci aktualniho behu programu. '''
  
  def __init__(self, options):
    self.options = options
    
  def __getitem__(self, key):
    return self.options[key]
  
  def __setitem__(self, key, val):
    self.options[key] = val
    
  def isHelp(self):
    return self.options['help']

  def __str__(self):
    ret = ""
    
    for i in self.options.items():
      ret += str(i[0]) + " : " + str(i[1])
      ret += '\n';
      
    return ret
  
def help():
  s  = "Jednoduchy makroprocesor JMP - ovladani:\n"
  s += "  --help              Vytiskne napovedu - nelze kombinovat\n"
  s += "  --input=filename    Definuje vstupni soubor (implicitne stdin)\n"
  s += "  --output=filename   Definuje vystupni soubor (implicine stdout)\n"
  s += "  --cmd=text          Vlozi 'text' na zacatek vystupni sekvence\n"
  s += "  -r                  Redefinice makra pomoci @def skonci s chybou\n"
  
  return s
 
def argparse(argv):
  """ Funkce pro zpracovani argumentu. Kontroluje integritu a format argumentu. Pri chybe
  vyhazuje InvalidArgsError vyjimku. Argument --help se nesmi vyskytnout spolu s jinymi argumenty.
  Lze tedy predpokladat, ze hodnota 'help' bude splnovat tuto konvenci.
  
  Vraci instanci tridy ConfigSet, ktera zapouzdruje hodnoty argumentu - pripadne jejich implicitni hodnoty.
  """
  
  default = {
      'help'   : False,
      'input'  : False,
      'output' : False,
      'cmd'    : "",
      'r'      : False
            }
  
  userArgs = {}
  
  for arg in argv[1:]:
    
    if arg == '--help':
      userArgs['help'] = True;
    
    elif arg.startswith('--input='):
      userArgs['input'] = arg[8:]
      if not userArgs['input']: # je prazdny?
        raise InvalidArgsError("Missing value for --input argument.")
    
    elif arg.startswith('--output='):
      userArgs['output'] = arg[9:]
      if not userArgs['output']: # je prazdny?
        raise InvalidArgsError("Missing value for --output argument.")
    
    elif arg.startswith('--cmd='):
      
      userArgs['cmd'] = arg[6:]
      if not userArgs['cmd']: # je prazdny?
        raise InvalidArgsError("Missing value for --cmd argument.")
    
    elif arg == '-r':
      userArgs['r'] = True
      
    else:
      raise InvalidArgsError("Neznamy parametr: {}".format(arg))
    
    
  res = dict(list(default.items()) + list(userArgs.items()))
  
  if 'help' in userArgs.keys() and len(userArgs) > 1:
    raise InvalidArgsError("Invalid argument combination.")
  
  
  return ConfigSet(res)


# ---------------------------------------------------------------
# Hlavni pristupovy bod programu
# ---------------------------------------------------------------


if __name__ == '__main__':
  
  try:
    
    # zpracuj arguemnty a inicializuj ridici strukturu
    cfg = argparse(sys.argv);
    
  except InvalidArgsError as err:
    
    print( str(err), file=sys.stderr )
    sys.exit(INVALID_ARG_ERR)
    
  
  # - vytiskni napovedu
  if cfg.isHelp():
    print( help(), end="" )
    sys.exit(0)
    
  # spust makroprocesor
  try:
    proc = Processor(cfg)
  except (macro.IllegalMacroRedefinition) as err:
    print(err, file=sys.stderr)
    sys.exit(REDEF_ERR)
  
  try:
    proc.readfile()
  except Exception as ex:
    print( ex, file=sys.stderr )
    sys.exit( READ_FILE_ERR )
    
  # pokus se zpracovat soubor  
  try:
    output = proc.process()
  except (processor.BlockNotClosedError, processor.IllegalCharSequenceError, SyntaxError) as err:
    print( err, file=sys.stderr )
    sys.exit(SYNTAX_ERR)
  
  # kazda vyjimka nese informaci o chybe
  except (macro.UnknownMacroError, processor.ArgumentsError, macro.MacroNotDefinedError) as err:
    print(err, file=sys.stderr)
    sys.exit(SEMANTIC_ERR)
  
  except(macro.IllegalMacroRedefinition) as err:
    print(err, file=sys.stderr)
    sys.exit(REDEF_ERR)
    
    
    # ziskej deskriptor pro vystupni soubor ( stdout | soubor na disku )
  if cfg['output'] == False:
    fh = sys.stdout
  else:
    
    try:
      fh = open(cfg['output'], 'w')
    except Exception as err:
      print(err, file=sys.stderr)
      sys.exit(WRITE_FILE_ERR)
  

  fh.write(output)
  
  fh.close()
  



#JMP:xkovar66

from abc import ABCMeta, abstractmethod

import re, processor


class UnknownMacroError(Exception): pass
class IllegalMacroRedefinition(Exception): pass
class MacroNotDefinedError(Exception): pass
class ArgumentsError(Exception): pass

class MacroTable:
  ''' Tablulka maker. Zpristupnuje definici makra na zaklade jeho jmena a umoznuje
  s nimi manipulovat. Implicitne obsahuje definici vestavenych maker. '''
  
  def __init__(self, restrict = False):
    
    self.__macros = {}
    self.__macros['ahoj'] = ""
    self.__restrict = restrict
    
    self.__macros['@null'] = NullMacro()
    
    self.__macros['@let'] = self.__macros['@__let__'] = LetMacro()
    self.__macros['@set'] = self.__macros['@__set__'] = SetMacro()
    self.__macros['@def'] = self.__macros['@__def__'] = DefMacro()
    
    self.__immutable = ['@__def__', '@__set__', '@__let__']
    
      
  def exists(self, key):
    ''' Zjisti, zda makro daneho jmena existuje v tabulce '''
    return key in self.__macros.keys()
  
  @property
  def immutable(self):
    return tuple(self.__immutable)
  
  def __delitem__(self, key):
    del self.__macros[key]
  
  def __getitem__(self, key):
    return self.__macros[key]
  
  def __setitem__(self, key, val):
    
    if self.__restrict and key in self.__macros.keys():
      raise IllegalMacroRedefinition("Macro redefinition is forbid in restrict mode")
    
    if key in self.__immutable:
      raise IllegalMacroRedefinition("Macro {} can not be redefined".format(key))
    
    self.__macros[key] = val
    
  def __str__(self):
    return str(self.__macros)

class Macro():
  ''' Bazova trida pro definice maker. Definuje protokol jednotlivych maker.'''  
  def __init__(self, argc, name):
    self.__argc = argc
    self.__name = name 
    self.re_names = re.compile("\s*(?P<name>\$[a-zA-Z_][0-9a-zA-Z_]*)\s*")
    
  @property
  def argc(self):
    return self.__argc

  @property
  def name(self):
    return self.__name
  
  def expand(self):
    return ''
  
class NullMacro(Macro):
  ''' Prazdne makro. Je expandovano na prazdny retezec. Ma specialni vyznam az podle kontextu pouziti '''
  def __init__(self):
    Macro.__init__(self, 0, 'NullMacro')
    
  def expand(self):
    return ''
  
  
class LetMacro(Macro):
  ''' Makro pro vytvareni synonym. Primo manipuluje s tabulkou maker, ve ktere je schopno menit
  definice maker (kopirovat reference jinych maker pod prislusna jmena) ''' 
  
  def __init__(self):
    Macro.__init__(self, 2, 'LetMacro')
    
  def expand(self, table, arg1, arg2):
    ''' Expanduje makro se zadanymi argumenty. Expanduje se na prazdny retezec, expanze makra
    ma totiz vyznam po strance manipulace s tabulkou maker.'''
    #TODO: co kdyz makro neni definovane?
    
    if not table.exists(arg2):
      raise UnknownMacroError("Second argument of @let macro has to be defined")
  
    if arg1 == '@null': # pokud je prvni argument @null, nahrazeni je ignorovano
      return ''
    
    if arg2 == '@null': # pokud je druhy argument @null, makro arg1 je smazano z tabulky
      # konstantni makro nelze predefinovat => chyba 57
      if arg1 in table.immutable:
        raise IllegalMacroRedefinition("Macro {} can not be deleted".format(arg1))
        
      try: #pokus se smazat
        del table[arg1]
      except KeyError:
        pass
        
        
      return ''
    
    # jinak dojde k substituci
    table[arg1] = table[arg2]
    
    return ''
  
class SetMacro(Macro):
  ''' Makro pro manipulaci s rezimem lexikalniho analyzatoru. Umoznuje nastavit
  rezim cteni / ignorovani bilych znaku.'''
  def __init__(self):
    Macro.__init__(self, 1, 'SetMacro')

  def expand(self, scanner, val):
    ''' Makro akceptuje pouze argumenty +/-INPUT_SPACES. Po textove strance je expandovano
    na prazdny retezec. '''
    
    if val == '-INPUT_SPACES':
      scanner.ignoreWhitespace()
    
    elif val == '+INPUT_SPACES':
      scanner.acceptWhitespace()
    
    else:
      raise ArgumentsError('{0} accepts only values {-INPUT_SPACES|+INPUT_SPACES}')
    
    return ''
  
class DefMacro(Macro):
  ''' Makro pro definici  uzivatelskych maker. Vytvori novou polozku zadaneho jmena v tabulce maker
  a ulozi do nej definici noveho makra. 
  '''
  def __init__(self):
    Macro.__init__(self, 3, 'DefMacro')
    
  def containsDuplicates(self, names):
    return len(names) > len(set(names))
    
  def expand(self, table, name, args, body):
    ''' Textove je makro expandovano na prazdny retezec. Semantika makra spociva v manipulaci
    s tabublkou maker - definice novych maker. '''
    argNames = re.findall(self.re_names, args)
    
    if name == '@null': # pokud je prvni argument @null, nahrazeni je ignorovano
      return ''
    
    if self.containsDuplicates(argNames):
      raise ArgumentsError("Second block of @def macro contains duplicate values")
    
    bindings = [] # uchovava vazby v tele makra na nazvy argumentu
    
    for m in self.re_names.finditer(body):
      
      # kontrola, aby se $x na zacatku bloku nedodstalo na index -1
      
      if m.group('name') in argNames:
        bindings.append( (m.start('name'), m.group('name') ))
        
    
    # na vystupu je Definici uzivatelskeho makra ulozena do tabulky maker        
    table[name] = UserMacro(len(argNames), name, argNames, bindings, body)
     
        
    return ''
  
  
class UserMacro(Macro):
  ''' Uzivatelem definovane makro - v jazyce JMP vytvareno pomoci makra @def.
  Uzivatelske makro umoznuje pouze textove expanze, neni mozne manipulovat s tabulkou maker. '''
  
  def __init__(self, argc, name, args, bindings, body):
    ''' Bindings je pole dvojic (index, argument) '''
    
    Macro.__init__(self, argc, 'UserMacro:{}'.format(name))
    self.__args = args
    self.__bindigs = sorted(bindings, key=lambda arg: arg[0], reverse=True)
    self.__body = body
    self.__name = name
  
  @property
  def body(self):
    return self.__body
  
  @property
  def args(self):
    return self.__args
    
  def expand(self, *argv):
    ''' Textova expanze makra. Nahrazeni vsech vyskytu nazvu parametru jejich hodnotou '''
    
    res = self.__body
    
    for bind in self.__bindigs:

      start = bind[0]
      length = len(bind[1])
      
      res = res[:start] + argv[self.args.index(bind[1])] + res[start+length:]
      
       
    return res
  

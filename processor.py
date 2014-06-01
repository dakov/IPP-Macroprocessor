

#JMP:xkovar66

import sys
import re

from macro import *



class IllegalCharSequenceError(Exception): ''' Vyjimka popisujici neplatnou sekvenci znaku na vstupu.''' 
class BlockNotClosedError(Exception): ''' Vyjimka popisujici vyskyt neuzavreneho bloku na vstupu.''' 
class SyntaxClosedError(Exception): pass

class TooFewArgumentsError(Exception): ''' Vyjimka popisujici neplatnou variaci vstupnich argumentu. ''' 


class Processor:
  ''' Trida reprezentujici makroprocesor jazyku JMP. Ridi veskerou praci jednotlivych sekci trasformace, 
  expanzi maker a predavani dat mezi jednotlivymi sekcemi. '''
  def __init__(self, cfg):
    self.cfg = cfg
    
    self.readfile = self.generateReadfile()
    
    self.macroTable = MacroTable( cfg['r'] )
    
    
  def generateReadfile(self):
    """ Vraci volatelny objekt pro nacteni vstupu v zavislosti na tom, zda
    je vstupem soubor, nebo se cte ze standardniho vstupu """
    
    if ( not self.cfg['input'] ):
      return self.readStdin
    
    else:
      return self.readfile
    
  def readStdin(self):
    ''' Precte veskery text ze standardniho vstupu do retezce. Tento retezec
    ulozi do instancni promenne contents
    '''
    contents = ''
    
    while True:
        try:
            line = sys.stdin.readline()
        except KeyboardInterrupt:
            break
    
        if not line:
            break
    
        contents += line
        
    self.contents = self.cfg['cmd'] + contents
  
  def readfile(self):
    ''' Nacte obsah souboru zadaneho v konfiguraci tridy. Obsah ulozi do instancni promenne
    contents.
    '''
    
    with open(self.cfg['input'], 'r') as f:
      contents = f.read()
      
    self.contents = self.cfg['cmd'] + contents

    
    # pro kazdy argument provede jedno nacteni argument
    
  
  def expandMacro(self, macro):
    ''' Rozpozna typ makra, nacte jeho definici a provede odpovidijici akce a textovou expanzi. 
    Ocekava instanci tridy Macro jako prvni argument '''
    expansion = ""
    
    mtype = type(macro)
    args = []
    
    # prazdne macro -> nema zadny argument
    if mtype  == NullMacro:
      expansion = macro.expand()
    
    # let macro -> nacti 2 argumenty, oba musi byt typu makro
    elif mtype == LetMacro:
      
      for i in range(macro.argc): # => 2 argument
        token = self.scanner.getToken()
             
        if token is None:
          raise ArgumentsError('{0} expects {1} arguments, but {2} were given'.format(macro.name, macro.argc, i))
        
        if token[0] != self.scanner.s_macro: # typ argumentu neni nazev makra
          raise ArgumentsError('{0} expects arguments to be macro names'.format(macro.name))
        
        args.append(token[1])
        
      expansion = macro.expand(self.macroTable, *args) # proved expianz
      
    # set macro -> 1 argument typu block
    elif mtype == SetMacro:
      token = self.scanner.getToken()
      
      if token is None: # nedostate argumentu
        raise ArgumentsError('{0} expects {1} arguments, but {2} were given'.format(macro.name, macro.argc, i))
      
      if token[0] != self.scanner.s_block: # musi byt blok
          raise ArgumentsError('{0} expects arguments to be block'.format(macro.name))
      
      expansion = macro.expand(self.scanner, token[1])
    
    # makro @def -> 3 argumenty: nazev bamkra, blok, blok
    elif mtype == DefMacro: 
      token = self.scanner.getToken()

      # jmeno noveho makra 
      if token is None:
        raise ArgumentsError('{0} expects {1} arguments, but {2} were given'.format(macro.name, macro.argc, i))
      
      if token[0] != self.scanner.s_macro: # prvni argument musi byt nazev makra
          raise ArgumentsError('{0} expects arguments to be block'.format(macro.name))
      
      name = token[1]
      
      # blok argumentu noveho makra
      token = self.scanner.getToken()
      
      if token is None:
        raise ArgumentsError('{0} expects {1} arguments, but {2} were given'.format(macro.name, macro.argc, i))
      
      if token[0] != self.scanner.s_block: # druhy argument musi byt blok
          raise ArgumentsError('{0} expects arguments to be block'.format(macro.name))
        
      args = token[1]
      argblock_re = re.compile("^\s*((\$[a-zA-Z_][0-9a-zA-Z_]*)\s*)*$")
      
      if not re.match(argblock_re, args):
        raise SyntaxError("Second block of @def macro is not in expected format")
      # blok tela noveho makra
      token = self.scanner.getToken()
      
      if token is None:
        raise ArgumentsError('{0} expects {1} arguments, but {2} were given'.format(macro.name, macro.argc, i))
      
      if token[0] != self.scanner.s_block: # treti argument musi byt blok
          raise ArgumentsError('{0} expects arguments to be block'.format(macro.name))
        
      body = token[1]
      
      expansion = macro.expand(self.macroTable,name, args, body)
      
    # uzivatelske makro
    elif mtype == UserMacro:
      argv = []
      
      for i in range(macro.argc): # macro.argc obsahuje pocet argument, ktere se maji nacist
        token = self.scanner.getToken()
        if token is None:
          raise ArgumentsError("Too few arguments for macro '{}'".format(macro.name))
        
        argv.append(token[1])
      
      expansion = macro.expand(*argv)
      
    return expansion    
      
    
    
  def process(self, string=None):
    ''' Prijme retezec urceny ke zpracovani a vraci jeho podobu po kompletni expanzi  '''
    
    output = ""
    
    if string is None:
      string = self.contents
      
    content = ExtendableString(string)
    
    self.scanner = Scanner(content)
    
    while True:
      # zpracovani makra probiha v jedne iteraci tohoto cyklu, proto v kazde iteraci vytvorime zalohu,
      # je tedy garantovano, ze zaloha bude na konci zpracovani makra stale ta sama
      pointerBck = content.createBackup() 
      
      # nacti jednu lexikalni jednotku
      token = self.scanner.getToken()

      if token is None: # konec souboru
        break
      
      typ, value = token
      
      if typ == self.scanner.s_macro:
        
        if not self.macroTable.exists(value):
          raise MacroNotDefinedError("Macro {} is not defined".format(value))
        
        expansion = self.expandMacro(self.macroTable[value]) # epanduje makro
        content.extend(expansion, pointerBck, content.pointer) # a pripoji expandovany retezec na zacatek vstupu

        content.doBackup() # provede zalohu ukazatele na aktualne cteny znak
        
      else:
        output += value
      
    return output
 
class Scanner:
  ''' Lexikalni analyzator makroprocessoru, rozlisuje tri typy lexikalnich jednotek: znak, blok, nazev marka '''

  ( # definice stavu automatu
   s_idle,
   s_text,
   s_at,
   s_char,
   s_block_read,
   s_block,
   s_block_esc,
   s_macro,
   
   ) = range(8)
   
  
  def __init__(self, content):
    self.__content = content
    self.state = self.s_idle
    
    # implicitne prijima bile znaky
    self.acceptWhitespace()
    
   
  @property
  def content(self):
    return self.__content
  
  
  def ignoreWhitespace(self):
    ''' Nastavi analyzator do rezimu ignorovani bilych znaku '''
    self.__ignoreWhitespace = True
    
  def acceptWhitespace(self):
    ''' Nastavi analyzator do rezimu, kdy prijima bile znaky ''' 
    self.__ignoreWhitespace = False
    
    
  def getToken(self):
    ''' Nacte a vrati lexikalni jednotku a jeji typ ze vstupu. Vraci None, pokud dorazi na konec souboru '''
    
    state = self.s_idle
    blockCounter = 0
    buff = ""
    
    while True:
      
      try:
        ch = self.content.getc()
      except:
        ch = None
        
      if state == self.s_idle:
        
        if ch == '@':
          state = self.s_at
          buff += ch
        
        elif ch == '{':
          state = self.s_block_read
          blockCounter += 1
        
        elif ch in ('}', '$'):
          raise IllegalCharSequenceError("Char {} has to be escaped".format(ch))
        
        elif ch is None:
          return None
        
        else:
          if self.__ignoreWhitespace and ch.isspace():
            continue
          
          else:
            state = self.s_char
            buff += ch
            break
          
      elif state == self.s_at:
        
        if ch in ( '{', '}', '@', '$'):
          state = self.s_char
          buff = ch
          break
        
        elif ch.isalnum() or ch == '_':
          state = self.s_macro
          buff += ch
        
        else:
          raise IllegalCharSequenceError("Unknown escape sequence")
        
      elif state == self.s_block_read:
        
        if ch == '{':
          blockCounter += 1
          buff += ch
        
        elif ch == '}':
          blockCounter -= 1
          
          if blockCounter == 0:
            state = self.s_block
            break
          
          else:
            buff += ch
          
        elif ch == '@':
          state = self.s_block_esc
          
        elif ch is None:
          raise BlockNotClosedError('Defined block is incomplete')
        
        else:
          buff += ch
        
      elif state == self.s_block_esc:
        
        if ch in ( '{', '}', '@'):
          buff += ch
        
        else:
          buff += '@' + ch
        
        state = self.s_block_read
        
      elif state == self.s_macro:
        
        if ch is None:
          break
                
        if ch.isalnum() or ch == '_':
          buff += ch
          
        else:
          self.content.putback()
          break
        
          
    return state, buff

           
class ExtendableString:
  ''' Retezec s moznosti nahrazeni podretezce jinym retezcem. Umoznuje take sekvencni cteni retezece.
  Uchovava si ukazatel a aktualne cteny znak, po jeho precteni je ukazatel posunut na nasledujici znak.'''
  
  def __init__(self, string):      
    self.__content = string
    self.__pointer = 0
    
    self.__backup = 0
    
  
  def getc(self):
    ''' Nacte a vrati nasledujici znak z retezce (ridi se ukazatelem na aktualni znak). Pokud je na konci retezce
    vraci hodnotu None. '''
    ch = self.content[self.pointer]
    self.__pointer += 1
    
    return ch
  
  def putback(self, n=1):
    ''' Vrati N znaku zpet na vstup (posune cteci hlavu retezce o N znaku zpatky '''
    self.__pointer -= n
    
  def createBackup(self):
    ''' Vytvori zalohu pozice cteci hlavy, aby bylo mozne se na tuto pozici vratit '''
    self.__backup = self.pointer
    
    return self.pointer
    
  def doBackup(self):
    ''' Vrati cteci hlavu na pozici posledni zalohy. '''
    self.__pointer = self.__backup
  
  def extend(self, string, from_, to):
    ''' Na pozici cteci hlavy vsune novy podretezec, len urcuje delku nahrazovane sekvence'''
    self.__content = self.content[:from_] + string + self.content[to:]
  
  @property
  def content(self):
    ''' pozor vyhazuje vyjimku '''
    return self.__content
  
  @property
  def pointer(self):
    return self.__pointer
  
  @property
  def backup(self):
    return self.__backup
  
  def __str__(self):
    return self.content
  
  
  

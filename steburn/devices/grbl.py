"""GRBL transport with checked homing, alignment and job prerequisites."""
import re,time,math,threading
from collections import deque

class GrblSession:
    def __init__(self):
        self.serial=None; self.settings={}; self.firmware=''; self.origin_confirmed=False
        self.low_power_confirmed=False; self.low_power=0.; self.cancelled=threading.Event(); self.log=deque(maxlen=10000)
        self.homed=False; self.safety_reason='Referenzfahrt erforderlich'; self.margin=5.
        self.io_lock=threading.RLock()
        self.frame_stop=threading.Event(); self.link_ok=False
        self.last_position=None
        self.frame_light_requested=False; self.frame_light_power=.1; self.frame_light_changed=threading.Event(); self.framing=False
    def invalidate(self,reason):
        self.homed=False; self.origin_confirmed=False; self.low_power_confirmed=False
        self.safety_reason=reason
    def observe(self,value):
        """Every received line must pass here, including lines before status reports."""
        self.log.append(value)
        if value: self.link_ok=True
        if value.lower().startswith('grbl'):
            self.invalidate('Controller-Neustart: reale Position unbekannt. Neu referenzieren.')
            raise ValueError(self.safety_reason)
        if value.startswith('ALARM:'):
            self.invalidate(value+' – Referenzfahrt erforderlich')
            raise ValueError(self.safety_reason)
    def home(self):
        if self.cancelled.is_set(): self.resynchronize()
        self.invalidate('Referenzfahrt läuft')
        if self.settings.get(22)!=1: raise ValueError('Homing ist nicht aktiviert.')
        try:
            initial=self.status()
            if initial['state'] not in ('Idle','Alarm'): raise ValueError('Referenzfahrt benötigt Stillstand.')
            if initial['state']=='Idle': self.command('M5'); self.command('S0')
            self.command('$H',timeout=120)
            status=self.status()
            values=[float(v) for v in status.get('MPos','').split(',') if v]
            if status['state']!='Idle' or len(values)!=3 or not all(math.isfinite(v) for v in values) or any(abs(v)>.05 for v in values[:2]):
                raise ValueError('A40-Pro-Referenzposition nicht als 0/0 bestätigt.')
            self.command('G54'); self.command('G92.1'); self.command('G10 L2 P1 X0 Y0 Z0')
            if any(abs(v)>.001 for v in self.read_work_offset()):
                raise ValueError('Nullpunkt konnte nicht verifiziert werden.')
            self.homed=True; self.origin_confirmed=True
            self.safety_reason='Referenziert; G54-Nullpunkt eingerichtet'
            return self.safety_reason
        except Exception:
            self.emergency_stop()
            raise
    def resynchronize(self):
        if not self.connected: raise ValueError('Nicht verbunden')
        self.serial.reset_input_buffer()
        self.serial.write(b'\x18'); deadline=time.monotonic()+4; banner=False
        while time.monotonic()<deadline:
            line=self.serial.readline().decode(errors='replace').strip()
            self.log.append(line)
            if line.lower().startswith('grbl'): banner=True
            if banner and not line: self.cancelled.clear(); return
        raise TimeoutError('Kein Neustartbanner; Verbindung prüfen.')
    @property
    def connected(self): return self.serial is not None and self.serial.is_open
    def connect(self,port,baud):
        import serial
        self.disconnect(); self.cancelled.clear()
        self.serial=serial.Serial(port,int(baud),timeout=.15,write_timeout=1)
        self.origin_confirmed=False; self.low_power_confirmed=False; time.sleep(2)
        banner=self.serial.read(self.serial.in_waiting or 1).decode(errors='replace')
        try:
            info=self.command('$I'); settings=self.command('$$')
            self.firmware=banner+'\n'+'\n'.join(info)
            for line in settings:
                match=re.fullmatch(r'\$(\d+)=([-+\d.]+)',line.strip())
                if match: self.settings[int(match[1])]=float(match[2])
            if 'grbl' not in self.firmware.lower() and '[VER:1.1' not in self.firmware: raise ValueError('GRBL-1.1-Kompatibilität nicht bestätigt.')
        except Exception:
            self.disconnect(); raise
        return self.firmware+'\n'+'\n'.join(settings)
    def connect_and_home(self,port,baud):
        self.connect(port,baud)
        return self.home()
    def command(self,line,timeout=4):
        if self.cancelled.is_set(): raise ValueError('Vorgang abgebrochen. Neu verbinden erforderlich.')
        if not self.connected: raise ValueError('Kein Gerät verbunden.')
        self.log.append('> '+line); self.serial.write((line+'\n').encode('ascii')); lines=[]; deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            if self.cancelled.is_set(): raise ValueError('Abgebrochen')
            value=self.serial.readline().decode(errors='replace').strip()
            if not value: continue
            self.observe(value)
            if value=='ok': return lines
            if value.startswith(('error:','ALARM:')): raise ValueError(value)
            lines.append(value)
        self.invalidate('Zeitüberschreitung: Position unbekannt')
        raise TimeoutError('Controller antwortet nicht. Vorgang nicht automatisch fortsetzen.')
    def status(self):
        if not self.connected: raise ValueError('Nicht verbunden')
        self.serial.write(b'?'); deadline=time.monotonic()+2
        while time.monotonic()<deadline:
            value=self.serial.readline().decode(errors='replace').strip()
            self.observe(value)
            if value.startswith('<') and value.endswith('>'):
                parts=value[1:-1].split('|'); data={'state':parts[0]}
                for part in parts[1:]:
                    if ':' in part:
                        k,v=part.split(':',1); data[k]=v
                return data
        self.invalidate('Kein frischer Controllerstatus; neu referenzieren')
        self.link_ok=False
        raise TimeoutError('Kein frischer Controllerstatus')
    def ready(self,width,height):
        if not self.homed: raise ValueError(self.safety_reason)
        if not self.origin_confirmed: raise ValueError('Ursprung, Homing und Nullpunkt noch nicht bestätigt.')
        if any(self.settings.get(k)!=1 for k in (20,21,22)):
            raise ValueError('Soft Limits, Hard Limits und Homing ($20/$21/$22=1) erforderlich.')
        if not all(math.isfinite(self.settings.get(k,float('nan'))) for k in (30,32,130,131)): raise ValueError('Unvollständige oder ungültige Controllerparameter')
        if self.settings.get(13)!=0: raise ValueError('$13=0 (Status in Millimetern) erforderlich; Steburn ändert keine Einstellungen.')
        if self.settings.get(32)!=1 or self.settings.get(30,0)<=0: raise ValueError('$32=1 und gültiges $30 erforderlich. Steburn ändert keine Firmwareeinstellungen.')
        if abs(self.settings.get(130,0)-width)>.01 or abs(self.settings.get(131,0)-height)>.01: raise ValueError('Controller-Arbeitsfläche stimmt nicht mit Projekt überein.')
        status=self.status()
        if not self.homed: raise ValueError(self.safety_reason)
        if status['state']!='Idle': raise ValueError('Controller muss Idle sein: '+status['state'])
        if 'MPos' in status and 'WPos' not in status and 'WCO' not in status:
            offset=self.read_work_offset()
            status=self.status()
            if status['state']!='Idle': raise ValueError('Controller wurde während der Prüfung aktiv.')
            if 'WPos' not in status and 'WCO' not in status: status['WCO']=','.join(str(v) for v in offset)
        if 'WPos' in status: pos=[float(v) for v in status['WPos'].split(',')]
        elif 'MPos' in status and 'WCO' in status:
            pos=[a-b for a,b in zip(map(float,status['MPos'].split(',')),map(float,status['WCO'].split(',')))]
        else: raise ValueError('Arbeitsposition nicht eindeutig. WPos oder MPos+WCO erforderlich.')
        if len(pos)<2 or not all(math.isfinite(v) for v in pos) or not (0<=pos[0]<=width and 0<=pos[1]<=height): raise ValueError('Aktuelle Position außerhalb bestätigter Arbeitsfläche.')
        return pos[:2]
    def check_targets(self,points,width,height):
        if not points or any(len(pt)!=2 or not all(math.isfinite(v) for v in pt) or not (self.margin<=pt[0]<=width-self.margin and self.margin<=pt[1]<=height-self.margin) for pt in points):
            raise ValueError(f'Ziel außerhalb des vorläufigen Innenbereichs ({self.margin:g} mm Randabstand). Mechanische Nutzfläche noch nicht vollständig vermessen.')
    def realtime(self,value):
        if value not in (0x21,0x7e,0x85,0x90,0x91,0x92,0x93,0x94,0x99,0x9a,0x9b,0x9c,0x9d): raise ValueError('Unbekannter Echtzeitbefehl')
        if not self.connected: raise ValueError('Nicht verbunden')
        self.log.append(f'> realtime 0x{value:02x}'); self.serial.write(bytes([value]))
    def read_work_offset(self):
        """GRBL may omit WCO from individual reports. Read active WCS and G92 explicitly."""
        modal=self.command('$G')
        active=[]
        for line in modal:
            if line.startswith('[GC:'):
                active.extend(re.findall(r'(?<![\w.])G(5[4-9])(?![\d.])',line))
        if len(active)!=1: raise ValueError('Aktives Koordinatensystem nicht eindeutig; keine Bewegung.')
        records={}
        for line in self.command('$#'):
            match=re.fullmatch(r'\[([^:]+):([^\]]+)\]',line)
            if match: records[match[1]]=match[2]
        def vector(key):
            if key not in records: raise ValueError('Koordinatenversatz fehlt: '+key)
            values=[float(v) for v in records[key].split(',')]
            if len(values)!=3 or not all(math.isfinite(v) for v in values): raise ValueError('Ungültiger Versatz: '+key)
            return values
        base=vector('G'+active[0]); temporary=vector('G92')
        return [base[i]+temporary[i] for i in range(3)]
    def diagnostics(self):
        if self.settings.get(13)!=0: raise ValueError('Diagnose benötigt Positionsanzeige in mm ($13=0).')
        status=self.status(); modal=self.command('$G'); offsets=self.command('$#')
        return 'Status: '+str(status)+'\n'+'\n'.join(modal+offsets)
    def wait_idle(self):
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            if self.cancelled.is_set(): raise ValueError('Abgebrochen')
            state=self.status()['state']
            if state=='Idle': return
            if state not in {'Run','Jog'}: raise ValueError('Controllerzustand '+state)
            time.sleep(.05)
        raise TimeoutError('Bewegung nicht rechtzeitig abgeschlossen')
    def align(self,points,width,height,visible=False,pulse=False):
        self.check_targets(points,width,height)
        self.ready(width,height)
        if visible and (not self.low_power_confirmed or not 0<self.low_power<=.5): raise ValueError('Sichtbare Ausrichtung benötigt separat getestete Leistung (max. 0.5 %). Kein Wert garantiert spurenfreies Material.')
        sval=math.floor(self.settings[30]*self.low_power/100) if visible else 0
        if visible and sval<1: raise ValueError('Leistung liegt unter Controllerauflösung. Keine automatische Erhöhung.')
        try:
            # Device coordinates are only accepted with a zero G54/G92 offset.
            modal=self.command('$G')
            if not any(re.search(r'\bG54\b',line) for line in modal): raise ValueError('G54 muss aktiv sein.')
            if any(abs(v)>.001 for v in self.read_work_offset()): raise ValueError('Ausrichtung benötigt G54/G92 ohne Versatz.')
            self.command('M5'); self.command('S0'); self.command('G21'); self.command('G90'); self.command('G94')
            x,y=points[0]; self.command(f'G1 X{x:.4f} Y{y:.4f} F1200'); self.wait_idle()
            if visible and pulse:
                self.command(f'M3 S{sval}'); self.command('G4 P0.1'); self.command('M5'); self.wait_idle()
            else:
                if visible: self.command(f'M4 S{sval}')
                for x,y in points[1:]:
                    self.command(f'G1 X{x:.4f} Y{y:.4f} F1200'); self.wait_idle()
                self.command('M5')
        except Exception:
            self.emergency_stop(); raise
    def emergency_stop(self):
        self.invalidate('Reset angefordert: reale Position unbekannt')
        self.cancelled.set(); self.origin_confirmed=False; self.low_power_confirmed=False
        if self.connected:
            try: self.serial.write(b'\x18')
            except Exception: pass
    def configure_frame_light(self,enabled,power=.1):
        if type(power) not in (float,int) or not math.isfinite(power) or not 0<power<=.5: raise ValueError('Rahmenlicht benötigt >0 bis maximal 0,5 %. Auch schwache Leistung kann Spuren hinterlassen.')
        self.frame_light_requested=bool(enabled); self.frame_light_power=float(power); self.frame_light_changed.set()
    def frame_light_sval(self):
        return self.weak_light_sval(self.frame_light_power)
    def weak_light_sval(self,power):
        if type(power) not in (int,float) or not math.isfinite(power) or not 0<power<=.5: raise ValueError('Pointer-/Rahmenlicht: mehr als 0 bis maximal 0,5 %. Auch geringe Leistung kann Spuren erzeugen.')
        if self.settings.get(31)!=0: raise ValueError('Rahmenlicht benötigt $31=0. Firmwarewerte werden nicht automatisch geändert.')
        sval=math.floor(self.settings[30]*power/100)
        if sval<1: raise ValueError('Rahmenlicht liegt unter der Controllerauflösung; keine automatische Leistungserhöhung.')
        return sval
    def wait_jog(self,timeout=120,allow_light_change=False,target=None):
        """Only this serial reader sends cancel; require two stable Idle reports.

        A button only sets the stop event. Repeated asynchronous cancels and a
        single stale status must not race the next G-code command.
        """
        deadline=time.monotonic()+timeout; cancel_sent=False; previous=None
        while time.monotonic()<deadline:
            cancelled=self.frame_stop.is_set() or (allow_light_change and self.frame_light_changed.is_set())
            if cancelled and not cancel_sent: self.realtime(0x85); cancel_sent=True
            status=self.status(); pos=self.position(status)
            if status['state']=='Idle':
                if previous is not None and math.dist(previous,pos)<=.005 and (cancelled or target is None or math.dist(pos,target)<=.05): self.last_position=pos; return status
                previous=pos
            elif status['state']=='Jog' or (cancelled and status['state']=='Hold:1'): previous=None
            else: raise ValueError('Unerwarteter Jog-Status: '+status['state'])
            time.sleep(.04)
        raise TimeoutError('Jog-Stillstand nicht bestätigt; Diagnose und Referenz prüfen.')
    def pointer_move(self,point,width,height,visible=False,power=.1):
        self.check_targets([point],width,height); self.ready(width,height)
        if any(abs(v)>.001 for v in self.read_work_offset()): raise ValueError('Pointerfahrt benötigt Nullversatz.')
        sval=self.weak_light_sval(power) if visible else 0
        self.frame_stop.clear(); self.realtime(0x99)
        try:
            self.command('M5'); self.command('S0')
            self.command(f'$J=G90 G21 X{point[0]:.4f} Y{point[1]:.4f} F1200'); status=self.wait_jog(target=point)
            if not self.frame_stop.is_set() and math.dist(self.position(status),point)>.05: raise ValueError('Pointerziel nicht bestätigt.')
            if sval and not self.frame_stop.is_set():
                # Queue the complete finite pulse including M5 in one write.
                # No host-side timer leaves a stationary laser enabled.
                self.serial.write(f'M3 S{sval}\nG4 P0.15\nM5\n'.encode('ascii'))
                accepted=0; deadline=time.monotonic()+4
                while accepted<3 and time.monotonic()<deadline:
                    line=self.serial.readline().decode(errors='replace').strip()
                    if not line: continue
                    self.observe(line)
                    if line=='ok': accepted+=1
                    elif line.startswith('error:'): raise ValueError(line)
                if accepted!=3: raise TimeoutError('Pointerlicht-Abschaltung nicht bestätigt.')
            return f'Pointer · X {self.last_position[0]:.2f} / Y {self.last_position[1]:.2f} mm · Position gültig'
        finally:
            if self.connected and not self.cancelled.is_set(): self.command('M5'); self.command('S0')
    def frame_loop(self,points,width,height,visible=None,low_power=None):
        if visible is not None: self.configure_frame_light(visible,.1 if low_power is None else low_power)
        self.frame_stop.clear()
        self.check_targets(points,width,height); self.ready(width,height)
        if any(abs(v)>.001 for v in self.read_work_offset()): raise ValueError('Rahmen benötigt Nullversatz.')
        if self.frame_light_requested: self.frame_light_sval()
        self.realtime(0x99)
        self.command('M5'); self.command('S0')
        self.framing=True; self.frame_light_changed.clear()
        try:
            while not self.frame_stop.is_set():
                for index,(x,y) in enumerate(points):
                    if self.frame_stop.is_set(): break
                    repeat=True
                    while repeat and not self.frame_stop.is_set():
                        repeat=False; self.frame_light_changed.clear()
                        sval=self.frame_light_sval() if index>0 and self.frame_light_requested else 0
                        self.command('M5'); self.command('S0')
                        if sval: self.command(f'G1 M4 S{sval}')
                        self.command(f'$J=G90 G21 X{x:.4f} Y{y:.4f} F1200')
                        self.wait_jog(allow_light_change=True,target=(x,y))
                        repeat=self.frame_light_changed.is_set() and not self.frame_stop.is_set()
                        self.command('M5'); self.command('S0')
            status=self.status(); pos=self.position(status)
            if status['state']!='Idle' or not 0<=pos[0]<=width or not 0<=pos[1]<=height: raise ValueError('Rahmen-Stopp nicht bestätigt.')
            self.last_position=pos
            return f'Rahmen gestoppt · X {pos[0]:.2f} / Y {pos[1]:.2f} mm · Position gültig'
        finally:
            self.framing=False
            if self.connected and not self.cancelled.is_set(): self.command('M5'); self.command('S0')
    def stop_frame(self):
        self.frame_stop.set()
    @staticmethod
    def position(status):
        values=[float(v) for v in status.get('MPos',status.get('WPos','')).split(',') if v]
        if len(values)<2 or not all(math.isfinite(v) for v in values): raise ValueError('Position fehlt oder ist ungültig.')
        return tuple(values[:2])
    def return_to_origin(self,notify=None):
        if not self.homed or not self.origin_confirmed: raise ValueError('Keine gültige Referenz für Rückfahrt.')
        self.command('M5'); self.command('S0'); self.command('G90 G21 G94')
        self.command('G53 G1 X0 Y0 F1200'); deadline=time.monotonic()+120
        while time.monotonic()<deadline:
            status=self.status()
            if notify: notify(status)
            if status['state']=='Idle':
                pos=self.position(status)
                if math.dist(pos,(0,0))>.05: raise ValueError('Nullposition nicht erreicht.')
                self.last_position=pos; return status
            if status['state']!='Run': raise ValueError('Rückfahrt unterbrochen: '+status['state'])
            time.sleep(.03)
        raise TimeoutError('Rückfahrt nicht bestätigt.')
    def disconnect(self):
        self.link_ok=False
        self.invalidate('Verbindung getrennt: Referenzfahrt erforderlich')
        if self.serial:
            if self.serial.is_open:
                try: self.serial.write(b'M5\n')
                except Exception: pass
                self.serial.close()
        self.serial=None; self.settings={}; self.origin_confirmed=False; self.low_power_confirmed=False

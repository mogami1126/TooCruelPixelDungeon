from pathlib import Path
import subprocess, re
root=Path(__file__).resolve().parent.parent
src=root/'core/src/main/java/com/shatteredpixel/shatteredpixeldungeon'
out=root/'.research/numeric-regression'; out.mkdir(parents=True,exist_ok=True)
def method(file, signature):
 s=(src/file).read_text(encoding='utf-8'); a=s.index(signature); b=s.index('{',a)+1; n=1
 while n:
  n+=(s[b]=='{')-(s[b]=='}'); b+=1
 return s[a:b]
actor=(src/'actors/Actor.java').read_text(encoding='utf-8')
actor=actor[actor.index('public abstract class Actor'):].replace('public abstract class Actor','static abstract class Actor',1)
classes=[]
for name in ['Magnitude','TurnTime','EquipmentGrowth']:
 s=(src/('utils/'+name+'.java')).read_text(encoding='utf-8'); classes.append(s[s.index('public final class'):].replace('public final class','static final class',1))
java=r'''import java.util.*;
public class NumericProbe {
 static void require(boolean b,String name){if(!b)throw new AssertionError(name);}
 interface Bundlable { void storeInBundle(Bundle b); void restoreFromBundle(Bundle b); }
 static class Bundle {
  Map<String,Object> data=new HashMap<>(); void put(String k,Object v){data.put(k,v);}
  String getString(String k){return (String)data.get(k);} Bundle getBundle(String k){return (Bundle)data.get(k);} boolean contains(String k){return data.containsKey(k);} float getFloat(String k){return ((Number)data.getOrDefault(k,0)).floatValue();}
  long getLong(String k){return ((Number)data.getOrDefault(k,0)).longValue();} int getInt(String k){return ((Number)data.getOrDefault(k,0)).intValue();}
 }
 static class SparseArray<T> extends HashMap<Integer,T>{}
 static class DeviceCompat { static int repairs; static void log(String tag,String msg){repairs++;} }
 static class Statistics {static float duration;}
 static class Sprite {boolean isMoving; void recoverMotion(){isMoving=false;notifyAll();}}
 static class Char extends Actor { Sprite sprite; int pos(){return 0;} boolean isAlive(){return true;} HashSet<Buff> buffs(){return new HashSet<>();} protected boolean act(){return false;} }
 static class Buff extends Actor {protected boolean act(){return false;}}
 static class Mob extends Char {}
 static class Blob extends Actor {protected boolean act(){return false;}}
 static class LevelObject extends Actor {protected boolean act(){return false;}}
 static class Level { HashMap<Integer,Blob> blobs=new HashMap<>(); List<LevelObject> objects=new ArrayList<>(); List<Mob> mobs(){return new ArrayList<>();} void fixDispositionedMobs(){} }
 static class Dungeon {static Char hero=new Char(); static Level level;}
 ACTOR
 TYPES
 static class TestActor extends Actor {int calls; float cost; TestActor(float cost,int priority){this.cost=cost;actPriority=priority;} protected boolean act(){calls++;spend(cost);return true;} void move(float t){spend(t);} void disable(){diactivate();} }
 static class Observer extends TestActor {Observer(){super(1,-100);move(1);} protected boolean act(){calls++;Actor.keepActorThreadAlive=false;return true;}}
 static class Charger {int curCharges=1,maxCharges=10; float partialCharge; void updateQuickslot(){} GAIN }
 public static void main(String[] args)throws Exception {
  Magnitude huge=Magnitude.power(1.2,100001); require(huge.exponent()>7900,"huge exponent");
  Bundle largeSave=new Bundle();huge.store(largeSave,"large");require(huge.compareTo(Magnitude.restore(largeSave,"large"))==0,"magnitude save roundtrip");
  require(huge.multiply(Magnitude.ZERO).compareTo(Magnitude.ZERO)==0,"zero damage");
  require(huge.subtract(huge).compareTo(Magnitude.ZERO)==0,"lethal subtraction");
  require(Magnitude.of(Double.MIN_VALUE).mantissa()>=1,"subnormal construction");
  require(Float.isFinite(huge.finiteFloat()),"finite boundary");
  for(int b:new int[]{-100000,-70,0,10,38,70,1000,100000}) {
   float speed=EquipmentGrowth.speed(1.2,b);require(speed>=1f/64&&speed<=64,"bounded speed");
   require(TurnTime.delta(1f/speed)>0,"positive cost");
   require(Float.isFinite(EquipmentGrowth.charge(1.2,b)),"finite charge");
  }
  require(Math.abs(EquipmentGrowth.speed(1.2,5)-Math.pow(1.2,5))<1e-6,"ordinary speed unchanged");
  require(TurnTime.delta(1e-12f)==1,"small positive preserved");require(TurnTime.delta(-1e-12f)==-1,"refund preserved");
  require(TurnTime.delta(0)==0,"same time preserved");require(TurnTime.delta(Float.NaN)>0,"NaN repair");
  require(TurnTime.legacy(2_000_000f)==2_000_000L*TurnTime.UNITS,"legacy absolute timestamps must not be clipped to delta limit");
  require(TurnTime.legacy(3_000_000f)>TurnTime.legacy(2_000_000f),"legacy long games retain event ordering");
  TestActor a=new TestActor(0,0);a.move(.00001f);Bundle save=new Bundle();a.storeInBundle(save);
  TestActor loaded=new TestActor(0,0);loaded.restoreFromBundle(save);require(a.getTime()==loaded.getTime(),"new save exact");
  Bundle old=new Bundle();old.put("time",.5f);loaded.restoreFromBundle(old);require(loaded.getTime()==.5f,"legacy save");
  Charger charger=new Charger();charger.gainCharge(Float.POSITIVE_INFINITY);require(charger.curCharges==10&&charger.partialCharge==0,"infinite charging terminates");
  charger.curCharges=1;charger.gainCharge(Float.NaN);require(charger.curCharges==1,"NaN charging ignored");
  Actor.clear(); Actor.keepActorThreadAlive=true; TestActor stuck=new TestActor(0,0);Observer observer=new Observer();
  Actor.add(stuck);Actor.add(observer);Thread thread=new Thread(Actor::process);thread.setDaemon(true);thread.start();thread.join(3000);
  require(!thread.isAlive()&&observer.calls==1,"zero time cannot starve observer");
  require(DeviceCompat.repairs==1&&stuck.calls<=2080,"guard once logging bounded repetitions");
  Actor.clear();Actor.keepActorThreadAlive=true;TestActor inactive=new TestActor(0,100);inactive.disable();observer=new Observer();Actor.add(inactive);Actor.add(observer);
  thread=new Thread(Actor::process);thread.setDaemon(true);thread.start();thread.join(3000);
  require(!thread.isAlive()&&inactive.calls==0,"inactive not selected");
  System.out.println("PASS actual Actor scheduler: zero-time starvation guard, inactive exclusion, exact new/legacy saves; Magnitude huge powers, lethal/zero arithmetic; bounded rings; finite/refund time; actual Wand infinite charge");
 }
}
'''
java=java.replace('ACTOR',actor).replace('TYPES','\n'.join(classes)).replace('GAIN',method('items/wands/Wand.java','public void gainCharge(float charge)'))
(out/'NumericProbe.java').write_text(java,encoding='utf-8')
subprocess.run(['javac','-encoding','UTF-8',str(out/'NumericProbe.java')],check=True)
r=subprocess.run(['java','-cp',str(out),'NumericProbe'],capture_output=True,text=True,timeout=15)
print(r.stdout);print(r.stderr);r.check_returncode()
(out/'output.txt').write_text(r.stdout,encoding='utf-8')

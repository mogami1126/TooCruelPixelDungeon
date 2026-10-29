"""Probe real Actor/Char spend methods with minimal engine stubs; no device claims."""
import ast
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parent.parent
src = root / 'core/src/main/java/com/shatteredpixel/shatteredpixeldungeon'
out = root / '.research/scheduling-interaction'
out.mkdir(parents=True, exist_ok=True)

def method(file, signature):
    text = (src / file).read_text(encoding='utf-8')
    start = text.index(signature)
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]

# Reuse only the existing harness scaffold, without executing its tests.
tree = ast.parse((root / 'tools/numeric_regression.py').read_text(encoding='utf-8'))
java = next(ast.literal_eval(node.value) for node in tree.body
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'java' for t in node.targets))
java = java[:java.index(' public static void main(')]
java = java.replace('protected boolean act(){return false;} }\n static class Buff',
                    method('actors/Char.java', 'protected void spend( float time )') + ' protected boolean act(){return false;} }\n static class Buff', 1)
char_support = '''int HP=50,HT=100,attack,defense;
 int attackSkill(Char other){return attack;} int defenseSkill(Char other){return defense;}
 <T> T buff(Class<T> type){return null;}
 <T> HashSet<T> buffs(Class<T> type){return new HashSet<>();}
'''
char_source = (src / 'actors/Char.java').read_text(encoding='utf-8')
for name in ['INFINITE_ACCURACY', 'INFINITE_EVASION']:
    start = char_source.index('public static int ' + name)
    char_support += char_source[start:char_source.index(';', start)+1]
char_support += method('actors/Char.java', 'public static boolean hit( Char attacker, Char defender, float accMulti )')
java = java.replace('static class Char extends Actor {', 'static class Char extends Actor {' + char_support)
java += r'''
 static class Challenges {static final Challenges GRINDING_3=new Challenges();boolean enabled(){return false;}}
 static class MMO {static float skillMod(){return 1;}}
 static class Bless {} static class Hex {}
 static class ChampionEnemy {float accuracyFactor(){return 1;}float evasionFactor(){return 1;}}
 static class Random {static int calls;static float Float(float max){calls++;return max*.5f;}}
 static class RingOfTenacity {
   static int bonus; static class Tenacity {}
   static int getBuffedBonus(Char c,Class<?> type){return bonus;}
   TENACITY
 }
 static class CostChar extends Char {void move(float cost){spend(cost);} }
 static class Chain extends TestActor {
   final int length; final float[] costs;
   Chain(int length,float... costs){super(0,0);this.length=length;this.costs=costs;}
   protected boolean act(){
     if(calls==length){Actor.keepActorThreadAlive=false;Actor.remove(this);return true;}
     calls++;spend(costs[(calls-1)%costs.length]);return true;
   }
 }
 static void run(Chain chain)throws Exception {
   Actor.clear();DeviceCompat.repairs=0;Actor.keepActorThreadAlive=true;Actor.add(chain);
   Thread thread=new Thread(Actor::process);thread.setDaemon(true);thread.start();thread.join(3000);
   require(!thread.isAlive(),"finite chain terminates");
 }
 public static void main(String[] args)throws Exception {
   CostChar c=new CostChar();c.move(1f);require(c.getTime()==1f,"ordinary cost");
   c.clearTime();c.move(1e-12f);require(c.getTime()==1f/64,"positive lower bound");
   c.clearTime();c.move(100f);require(c.getTime()==64f,"long cost upper bound");
   c.clearTime();c.move(0f);require(c.getTime()==0f,"zero cost preserved");
   c.move(-.25f);require(c.getTime()==-.25f,"refund preserved");
   Chain shortZero=new Chain(31,0);run(shortZero);
   require(shortZero.calls==31&&DeviceCompat.repairs==0,"31 continuing zero actions allowed");
   Chain longZero=new Chain(32,0);run(longZero);
   require(longZero.calls==32&&DeviceCompat.repairs==1&&longZero.getTime()==1f/64,"32 continuing zero actions deferred");
   Chain refund=new Chain(10,-.25f);run(refund);
   require(DeviceCompat.repairs==0&&refund.getTime()==-2.5f,"finite refund chain preserved");
   Chain mixed=new Chain(100,0,1);run(mixed);
   require(DeviceCompat.repairs==0&&mixed.getTime()==50f,"progress resets counter");
   Char attacker=new Char(),defender=new Char();
   attacker.attack=Integer.MAX_VALUE;defender.defense=1;Random.calls=0;
   require(Char.hit(attacker,defender,1)&&Random.calls==0,"saturated accuracy uses guaranteed hit branch");
   defender.defense=Integer.MAX_VALUE;
   require(!Char.hit(attacker,defender,1)&&Random.calls==0,"saturated evasion wins both thresholds");
   RingOfTenacity.bonus=100000;
   require(RingOfTenacity.damageMultiplier(defender)==0,"large positive tenacity underflows to zero at half HP");
   require((float)Math.pow(.85,100000*.5f)==RingOfTenacity.damageMultiplier(defender),"same underflow as base formula");
   RingOfTenacity.bonus=0;
   require(RingOfTenacity.damageMultiplier(defender)==1,"ordinary no-ring reduction");
   System.out.println("PASS real Char.spend: ordinary, lower/upper bounds, zero, refund");
   System.out.println("PASS real Actor: finite zero chain, guard boundary, finite refunds, mixed progress");
   System.out.println("OBSERVED real Char.hit: saturated evasion beats saturated accuracy without RNG");
   System.out.println("OBSERVED real RingOfTenacity: +100000 at half HP gives zero multiplier");
   System.out.println("LIMIT: long legitimate zero-time chains are also deferred; no full challenge/device coverage");
 }
}
'''
actor = (src / 'actors/Actor.java').read_text(encoding='utf-8')
actor = actor[actor.index('public abstract class Actor'):].replace('public abstract class Actor', 'static abstract class Actor', 1)
types = []
for name in ['Magnitude', 'TurnTime', 'EquipmentGrowth']:
    code = (src / ('utils/' + name + '.java')).read_text(encoding='utf-8')
    types.append(code[code.index('public final class'):].replace('public final class', 'static final class', 1))
java = java.replace('ACTOR', actor).replace('TYPES', '\n'.join(types)).replace('GAIN', method('items/wands/Wand.java', 'public void gainCharge(float charge)'))
java = java.replace('TENACITY', method('items/rings/RingOfTenacity.java', 'public static float damageMultiplier( Char t )'))
(out / 'NumericProbe.java').write_text(java, encoding='utf-8')
subprocess.run(['javac', '-encoding', 'UTF-8', str(out / 'NumericProbe.java')], check=True)
result = subprocess.run(['java', '-cp', str(out), 'NumericProbe'], capture_output=True, text=True, timeout=15)
print(result.stdout, end='')
print(result.stderr, end='')
result.check_returncode()
(out / 'output.txt').write_text(result.stdout, encoding='utf-8')

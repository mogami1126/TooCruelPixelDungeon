from pathlib import Path
import json, hashlib, re, subprocess

root = Path(__file__).resolve().parent.parent
src = root / 'core/src/main/java/com/shatteredpixel/shatteredpixeldungeon'
out = root / '.research/boss-regression'
out.mkdir(exist_ok=True)
copied = []

def method(relative, signature, scope=None):
    text = (src / relative).read_text(encoding='utf-8')
    start = text.index(signature, text.index(scope) if scope else 0)
    brace = text.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        if text[end] == '{': depth += 1
        elif text[end] == '}': depth -= 1
        end += 1
    result = text[start:end]
    copied.append({'file': relative, 'signature': signature, 'line': text[:start].count('\n')+1,
                   'method_sha256': hashlib.sha256(result.encode()).hexdigest()})
    return result

play = method('sprites/CharSprite.java', 'public void play(Animation anim)')
move = method('sprites/TenguSprite.java', 'public void move( int from, int to, float moveIntervalMultiplier )')
complete = method('sprites/TenguSprite.java', 'public void onComplete( Animation anim )')
idle = method('sprites/TenguSprite.java', 'public void idle()')
king_damage = method('actors/mobs/DwarfKing.java', 'public void damage(int dmg, Object src)')
king_alive = method('actors/mobs/DwarfKing.java', 'public boolean isAlive()')
king_invuln = method('actors/mobs/DwarfKing.java', 'public boolean isInvulnerable(Class effect)')
barrier_act = method('actors/buffs/Barrier.java', 'public boolean act()')
barrier_inc = method('actors/buffs/Barrier.java', 'public void incShield(int amt)')
dk_act = method('actors/mobs/DwarfKing.java', 'public boolean act()', 'public static class DKBarrior')
tengu_play = method('sprites/TenguSprite.java', 'public void play(Animation anim)')
king_enter = method('actors/mobs/DwarfKing.java', 'private void enterFinalPhase()')
king_threshold = method('actors/mobs/DwarfKing.java', 'private int phaseShieldThreshold(int defeatedSubjects)')
recover_motion = method('sprites/CharSprite.java', 'public synchronized void recoverMotion()')
recover_wait = method('actors/Actor.java', 'public static boolean recoverStalledMotion(boolean manual)')

java = r'''
import java.util.*;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
public class BossProbe {
  static void require(boolean condition, String name) { if (!condition) throw new AssertionError(name); }
  static class Animation {}
  static boolean fast;
  static class Char { CharSprite sprite; int pos(){return 7;} }
  static class Motion { void stop(boolean complete){} void killAndErase(){} }
  static class EngineSprite {
    Animation curAnim, idle = new Animation(), die = new Animation(), run = new Animation();
    volatile boolean isMoving;
    int visualCell;
    Char ch;
    Motion motion;
    void place(int to) { visualCell=to; }
    void turnTo(int from, int to) {}
    public void play(Animation a) { curAnim=a; }
    public void onComplete(Animation a) {}
    public void idle() { play(idle); }
  }
  static class CharSprite extends EngineSprite {
    boolean fast() { return BossProbe.fast; }
    boolean canSkipAnimation(Animation a) { return a!=idle && a!=die; }
    PLAY
    RECOVERMOTION
  }
  static class TenguSprite extends CharSprite {
    TENGUPLAY
    IDLE
    MOVE
    COMPLETE
  }
  static class Sprite {
    void showStatus(int a,String b) {}
    void idle() {}
    Sprite centerEmitter() { return this; }
    void start(Object a, float b, int c) {}
  }
  static class Actor {
    static final float TICK=1;
    void spend(float t) {}
    static volatile Char waitingForMotion;
    static volatile long motionWaitStarted;
    static volatile boolean motionRecoveryAttempted;
    RECOVERWAIT
  }
  static class Shield extends Actor {
    int value;
    boolean detached;
    void detach() { detached=true; }
    public void incShield() { incShield(1); }
    public void incShield(int amt) { value+=amt; }
    int shielding() { return detached?0:value; }
    int absorbDamage(int dmg) {
      if (value>=dmg) { value-=dmg; dmg=0; }
      else { dmg-=value; value=0; }
      if (value==0) detach();
      return dmg;
    }
    public boolean act() { return true; }
    Shield setShield(int amount) { value=amount; return this; }
  }
  static class Barrier extends Shield {
    float partialLostShield;
    INC
    BARRIERACT
  }
  static class DKBarrior extends Barrier { DKACT }
  enum Property { IMMOVABLE }
  static class Mob extends Actor {
    int HP=50, HT;
    int deathCalls;
    boolean removed;
    Sprite sprite=new Sprite();
    Shield shield=new DKBarrior();
    Set<Property> properties=new HashSet<>();
    public boolean isAlive() { return HP>0; }
    public boolean isInvulnerable(Class cl) { return false; }
    boolean isImmune(Class cl) { return false; }
    <T> T buff(Class<T> cl) { return null; }
    int shielding() { return shield.shielding(); }
    Set<Property> properties() { return properties; }
    public void damage(int dmg,Object source) {
      // Minimal substitute for Char.damage: preserve alive gate, shield absorption,
      // HP clamping and virtual isAlive/death order. Other buffs are absent.
      if (!isAlive() || dmg<0 || isInvulnerable(source.getClass())) return;
      if (shielding()>0) dmg=shield.absorbDamage(dmg);
      HP-=dmg;
      if (HP<0) HP=0;
      if (!isAlive()) die(source);
    }
    void die(Object cause) { deathCalls++; removed=true; }
  }
  static class Ghoul extends Mob {}
  static class Monk extends Mob {}
  static class Warlock extends Mob {}
  static class Golem extends Mob {}
  static class Summoning { void detach() {} }
  static class KingDamager {}
  static class LockedFloor { void addTime(int t) {} }
  static class Hero { <T> T buff(Class<T> c) { return null; } String name() { return "hero"; } }
  static class Flag { boolean value; boolean enabled() { return value; } }
  static class Challenges { static Flag STRONGER_BOSSES=new Flag(); }
  static class Level {
    boolean[] water=new boolean[100];
    HashSet<Mob> roster=new HashSet<>();
    HashSet<Mob> mobs() { return roster; }
  }
  static class Dungeon { static Level level=new Level(); static Hero hero=new Hero(); }
  static class CityBossLevel { static int throne; }
  static class ScrollOfTeleportation { static void appear(Mob m,int p) {} }
  static class CharSpriteConstants { }
  static class Speck { static int SCREAM; static Object factory(int a){return null;} }
  static class Sample { static Sample INSTANCE=new Sample(); void play(Object a) {} }
  static class Assets { static class Sounds { static Object CHALLENGE; } }
  static class Messages { static String get(Object a,String b,Object... c) {return b;} }
  static class Viscosity {
    static class DeferedDamage { int pending; void prolong(int d){pending+=d;} }
  }
  static class Buff {
    static <T> T affect(Mob m,Class<T> cl) {
      try {
        T b=cl.getDeclaredConstructor().newInstance();
        if (b instanceof Shield) m.shield=(Shield)b;
        return b;
      } catch(Exception e) { throw new RuntimeException(e); }
    }
  }
  static class DwarfKing extends Mob {
    int phase=2, summonsMade=12;
    boolean deathResolved;
    float abilityCooldown,summonCooldown;
    <T> Set<T> buffs(Class<T> cl) {
      Set<T> result=new HashSet<>();
      if (cl==ShieldBuff.class && !shield.detached) result.add(cl.cast(shield));
      return result;
    }
    void yell(String s) {}
    KINGINVULN
    KINGALIVE
    KINGDAMAGE
    KINGENTER
    KINGTHRESHOLD
  }
  static class GameScene { static void ripple(int p) {} }
  public static void main(String[] args) throws Exception {
    TenguSprite normal=new TenguSprite();
    fast=false; normal.move(1,2,1); normal.onComplete(normal.run);
    require(!normal.isMoving,"normal completes");
    TenguSprite skipped=new TenguSprite();
    fast=true; skipped.move(1,2,1);
    require(!skipped.isMoving,"fast jump completes without stale flag");
    fast=false; normal.move(1,2,1); normal.play(normal.idle);
    require(!normal.isMoving,"interrupted jump clears moving");
    System.out.println("PASS Tengu: normal, fast, interrupted jump");
    Char pending=new Char(); pending.sprite=new CharSprite(); pending.sprite.ch=pending;
    pending.sprite.isMoving=true; pending.sprite.motion=new Motion();
    Actor.waitingForMotion=pending; Actor.motionWaitStarted=System.nanoTime();
    Actor.motionRecoveryAttempted=false;
    require(!Actor.recoverStalledMotion(false),"no premature automatic recovery");
    Actor.motionWaitStarted=System.nanoTime()-11_000_000_000L;
    require(Actor.recoverStalledMotion(false),"automatic movement recovery");
    require(!pending.sprite.isMoving && pending.sprite.visualCell==7 && pending.sprite.motion==null,"visual motion reconciled");
    require(!Actor.recoverStalledMotion(true),"recovery is once per wait");
    Actor.waitingForMotion=null;
    require(!Actor.recoverStalledMotion(true),"unrelated callback stalls refused");
    System.out.println("PASS Recovery: 10s gate, reconciliation, once-only, unsupported stall refusal");
    DKBarrior barrier=new DKBarrior(); barrier.value=100;
    for(int i=0;i<100;i++) barrier.act();
    require(barrier.value==100,"shield does not net-regenerate");
    System.out.println("BARRIER initial=100 after_100_ticks="+barrier.value);
    float scaling=(float)Math.pow(1.5f,19);
    int ht=300; ht*=scaling;
    int per=ht/12, residue=ht-12*per;
    require(residue>0,"MMO residue");
    DwarfKing broken=new DwarfKing(); broken.HT=ht; broken.shield.value=ht;
    for(int i=0;i<12;i++) broken.damage(per,new KingDamager());
    require(broken.phase==2 && broken.HP==50 && broken.shielding()==residue,"twelve deductions leave residue");
    for(int i=0;i<3;i++) broken.shield.act();
    int beforeFinal=broken.shielding();
    broken.damage(per,new KingDamager());
    require(broken.HP==50 && broken.phase==3 && broken.shielding()==0 && broken.deathCalls==0,"shield overkill does not kill protected HP");
    broken.damage(50,new Viscosity.DeferedDamage());
    require(broken.deathCalls==1 && broken.removed,"MMO final phase can die");
    System.out.println("KING_MMO HT="+ht+" per="+per+" residue="+residue+" shield_before_extra="+beforeFinal+" HP="+broken.HP+" phase="+broken.phase+" shield="+broken.shielding()+" death_calls="+broken.deathCalls+" removed="+broken.removed);
    DwarfKing control=new DwarfKing(); control.HT=300; control.shield.value=300;
    for(int i=0;i<12;i++) control.damage(25,new KingDamager());
    require(control.HP==50 && control.phase==3 && control.isAlive(),"normal transition");
    control.damage(50,new Viscosity.DeferedDamage());
    require(control.deathCalls==1 && control.removed,"normal final damage dies");
    System.out.println("KING_CONTROL HT=300 death_calls="+control.deathCalls+" removed="+control.removed);
    DwarfKing legacy=new DwarfKing(); legacy.HP=0; legacy.HT=ht;
    legacy.enterFinalPhase();
    require(legacy.deathCalls==1 && legacy.removed,"zero HP transition runs death");
    for(boolean strong:new boolean[]{false,true}) {
      Challenges.STRONGER_BOSSES.value=strong;
      int total=strong?18:12;
      for(int value:new int[]{300,450,665051,997577,Integer.MAX_VALUE}) {
        DwarfKing king=new DwarfKing(); king.HT=value; king.shield.value=value;
        int each=value/total;
        require(king.phaseShieldThreshold(total/3)==value-each*(total/3),"scaled wave threshold");
        for(int i=0;i<total;i++) king.damage(each,new KingDamager());
        if(king.phase==2) king.damage(each,new KingDamager());
        require(king.phase==3 && king.HP==50,"normal/strong scaling and int boundary");
        king.damage(50,new Viscosity.DeferedDamage());
        require(king.deathCalls==1,"final phase death at all scales");
      }
    }
    System.out.println("PASS King: legacy zero HP, normal/strong, scaled thresholds, INT_MAX");
  }
}
'''
for key, val in sorted([('PLAY', play), ('IDLE',idle), ('MOVE',move), ('COMPLETE',complete),
                 ('INC',barrier_inc), ('BARRIERACT',barrier_act), ('DKACT',dk_act),
                 ('KINGINVULN',king_invuln), ('KINGALIVE',king_alive), ('KINGDAMAGE',king_damage),
                 ('TENGUPLAY',tengu_play), ('KINGENTER',king_enter), ('KINGTHRESHOLD',king_threshold),
                 ('RECOVERMOTION',recover_motion), ('RECOVERWAIT',recover_wait)], key=lambda entry: -len(entry[0])):
    java=java.replace(key,val)
java=java.replace('class CharSprite extends EngineSprite {','class CharSprite extends EngineSprite { static final int POSITIVE=1, WARNING=2;')
java=re.sub(r'\bShield\b','ShieldBuff',java)
(out/'BossProbe.java').write_text(java,encoding='utf-8')
(out/'source-methods.json').write_text(json.dumps(copied,ensure_ascii=False,indent=2),encoding='utf-8')
print('Generated isolated harness with',len(copied),'verbatim source methods; other dependencies are stubs.')
subprocess.run(['javac','-encoding','UTF-8',str(out/'BossProbe.java')],check=True)
result=subprocess.run(['java','-cp',str(out),'BossProbe'],check=True,capture_output=True,text=True,timeout=15)
print(result.stdout)
(out/'output.txt').write_text(result.stdout,encoding='utf-8')

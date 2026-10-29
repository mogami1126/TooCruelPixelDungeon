from pathlib import Path
import subprocess

root = Path(__file__).resolve().parent.parent
src = root / 'core/src/main/java/com/shatteredpixel/shatteredpixeldungeon'
out = root / '.research/health-regression'
out.mkdir(parents=True, exist_ok=True)

def method(file, signature):
    text = (src / file).read_text(encoding='utf-8')
    start = text.index(signature)
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        if text[end] == '{': depth += 1
        elif text[end] == '}': depth -= 1
        end += 1
    return text[start:end]

health = (src / 'utils/HealthMath.java').read_text(encoding='utf-8')
health = health[health.index('public final class'):].replace('public final class', 'static final class', 1)
java = '''
public class HealthProbe {
  static void require(boolean ok, String label) { if (!ok) throw new AssertionError(label); }
  static class Buff { static final float TICK=1; boolean detached; void detach(){detached=true;} void spend(float time){} }
  static class Char { int HP, HT; boolean needsShieldUpdate; }
  static class RingOfMight { static float multiplier; static float HTMultiplier(Hero hero){return multiplier;} }
  static class ElixirOfMight { static class HTBoost { int boost(){return 107374186;} } }
  static class Hero extends Char {
    boolean resting; int lvl=1, HTBoost; ElixirOfMight.HTBoost boost;
    <T> T buff(Class<T> type){return type.cast(boost);}
    UPDATE
  }
  static class Healing extends Buff {
    Char target; int healingLeft; float percentHealPerTick; int flatHealPerTick;
    ACT
    TICKHEAL
    SET
    INCREASE
  }
  HEALTH
  static void pasty(Hero hero) { PASTY }
  static void carpaccio(Hero hero) { CARPACCIO }
  static class Chalice { int level(){return 10;} CHALICE }
  static class ShieldBuff {
    int shielding; Char target;
    int shielding(){return shielding;}
    SHIELDINC
  }
  static class ShieldOwner {
    boolean needsShieldUpdate=true;int cachedShield;
    java.util.List<ShieldBuff> shields=new java.util.ArrayList<>();
    java.util.List<ShieldBuff> buffs(Class<?> type){return shields;}
    SHIELDSUM
  }
  public static void main(String[] args) {
    ShieldBuff first=new ShieldBuff();first.shielding=Integer.MAX_VALUE-1;
    first.incShield(10);require(first.shielding==Integer.MAX_VALUE,"shield increment saturates");
    ShieldBuff second=new ShieldBuff();second.shielding=10;
    ShieldOwner owner=new ShieldOwner();owner.shields.add(first);owner.shields.add(second);
    require(owner.shielding()==Integer.MAX_VALUE,"stacked shield sum saturates");
    Hero foodHero=new Hero(); foodHero.HP=Integer.MAX_VALUE-2;foodHero.HT=Integer.MAX_VALUE;
    pasty(foodHero);require(foodHero.HP==Integer.MAX_VALUE,"pasty healing cannot overflow");
    foodHero.HP=Integer.MAX_VALUE-2;carpaccio(foodHero);
    require(foodHero.HP==Integer.MAX_VALUE,"carpaccio healing cannot overflow");
    foodHero.HP=Integer.MAX_VALUE-2;new Chalice().charge(foodHero,1);
    require(foodHero.HP==Integer.MAX_VALUE,"chalice healing cannot overflow");
    foodHero.HP=5;foodHero.HT=20;pasty(foodHero);require(foodHero.HP==7,"ordinary food healing");
    require(HealthMath.heal(10,20,Long.MAX_VALUE)==20,"long healing cannot wrap");
    Hero hero=new Hero(); hero.HT=Integer.MAX_VALUE; hero.HP=2_100_000_000;
    Healing heal=new Healing(); heal.target=hero; heal.setHeal(1_700_000_000, .25f, 0);
    heal.act(); require(hero.HP==Integer.MAX_VALUE, "healing HP addition must not wrap");
    require(heal.healingLeft==1_275_000_000, "heal reserve debited exactly once");
    heal.setHeal(Integer.MAX_VALUE, 1f, Integer.MAX_VALUE);
    require(heal.healingThisTick()==Integer.MAX_VALUE, "tick calculation must not wrap");
    heal.increaseHeal(Integer.MAX_VALUE);
    require(heal.healingLeft==Integer.MAX_VALUE, "stacked reserve must not wrap");
    hero.HT=20; hero.HP=5; heal.setHeal(30,.25f,0); heal.act();
    require(hero.HP==13 && heal.healingLeft==22, "ordinary healing preserved");
    hero.HT=hero.HP=20; hero.lvl=17; RingOfMight.multiplier=Float.POSITIVE_INFINITY;
    hero.boost=new ElixirOfMight.HTBoost(); hero.updateHT(true);
    require(hero.HT==Integer.MAX_VALUE && hero.HP==Integer.MAX_VALUE, "ring plus elixir must not wrap");
    hero.lvl=Integer.MAX_VALUE; hero.HTBoost=Integer.MAX_VALUE; hero.updateHT(true);
    require(hero.HT==Integer.MAX_VALUE && hero.HP==Integer.MAX_VALUE, "base level health must not wrap");
    hero.lvl=1; hero.HTBoost=0; hero.boost=null; RingOfMight.multiplier=1; hero.updateHT(false);
    require(hero.HT==20 && hero.HP==20, "unequip clamps to ordinary health");
    require(HealthMath.maximum(Double.NaN)==1, "invalid maximum never negative");
    System.out.println("PASS actual Healing/HeroupdateHT: ordinary healing, INT_MAX HP, stacked healing, infinite ring multiplier, elixir, level overflow, unequip; no immortality stubs");
    System.out.println("PASS real food/chalice assignments, Long.MAX_VALUE healing, shield increment and stacked shield sum");
  }
}
'''
for key, file, signature in [
    ('UPDATE', 'actors/hero/Hero.java', 'public void updateHT(boolean boostHP)'),
    ('ACT', 'actors/buffs/Healing.java', 'public boolean act()'),
    ('TICKHEAL', 'actors/buffs/Healing.java', 'private int healingThisTick()'),
    ('SET', 'actors/buffs/Healing.java', 'public void setHeal('),
    ('INCREASE', 'actors/buffs/Healing.java', 'public void increaseHeal('),
    ('CHALICE', 'items/artifacts/ChaliceOfBlood.java', 'public void charge(Hero target, float amount)'),
    ('SHIELDINC', 'actors/buffs/ShieldBuff.java', 'public void incShield( int amt )'),
    ('SHIELDSUM', 'actors/Char.java', 'public int shielding()'),
]:
    java = java.replace(key, method(file, signature))
for key, file in [('PASTY', 'items/food/Pasty.java'), ('CARPACCIO', 'items/food/FrozenCarpaccio.java')]:
    line = next(line.strip() for line in (src / file).read_text(encoding='utf-8').splitlines() if 'hero.HP =' in line)
    java = java.replace(key, line)
java = java.replace('HEALTH', health).replace('com.shatteredpixel.shatteredpixeldungeon.utils.HealthMath', 'HealthMath').replace('@Override', '')
(out / 'HealthProbe.java').write_text(java, encoding='utf-8')
subprocess.run(['javac', '-encoding', 'UTF-8', str(out / 'HealthProbe.java')], check=True)
result = subprocess.run(['java', '-cp', str(out), 'HealthProbe'], check=True, capture_output=True, text=True, timeout=15)
print(result.stdout)
(out / 'output.txt').write_text(result.stdout, encoding='utf-8')

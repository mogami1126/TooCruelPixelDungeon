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
  static class Char { int HP, HT; }
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
  public static void main(String[] args) {
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
  }
}
'''
for key, file, signature in [
    ('UPDATE', 'actors/hero/Hero.java', 'public void updateHT(boolean boostHP)'),
    ('ACT', 'actors/buffs/Healing.java', 'public boolean act()'),
    ('TICKHEAL', 'actors/buffs/Healing.java', 'private int healingThisTick()'),
    ('SET', 'actors/buffs/Healing.java', 'public void setHeal('),
    ('INCREASE', 'actors/buffs/Healing.java', 'public void increaseHeal('),
]:
    java = java.replace(key, method(file, signature))
java = java.replace('HEALTH', health).replace('com.shatteredpixel.shatteredpixeldungeon.utils.HealthMath', 'HealthMath').replace('@Override', '')
(out / 'HealthProbe.java').write_text(java, encoding='utf-8')
subprocess.run(['javac', '-encoding', 'UTF-8', str(out / 'HealthProbe.java')], check=True)
result = subprocess.run(['java', '-cp', str(out), 'HealthProbe'], check=True, capture_output=True, text=True, timeout=15)
print(result.stdout)
(out / 'output.txt').write_text(result.stdout, encoding='utf-8')

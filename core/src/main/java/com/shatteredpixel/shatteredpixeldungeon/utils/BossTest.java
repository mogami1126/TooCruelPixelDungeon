package com.shatteredpixel.shatteredpixeldungeon.utils;

import com.shatteredpixel.shatteredpixeldungeon.*;
import com.shatteredpixel.shatteredpixeldungeon.actors.Actor;
import com.shatteredpixel.shatteredpixeldungeon.actors.Char;
import com.shatteredpixel.shatteredpixeldungeon.actors.hero.HeroClass;
import com.shatteredpixel.shatteredpixeldungeon.actors.mobs.*;
import com.shatteredpixel.shatteredpixeldungeon.levels.*;
import com.shatteredpixel.shatteredpixeldungeon.scenes.*;
import com.shatteredpixel.shatteredpixeldungeon.windows.WndMessage;
import com.watabou.noosa.Game;
import com.watabou.utils.DeviceCompat;
import com.watabou.utils.PointF;

/** Explicitly enabled debug-only helpers. Boss state and death code are never overridden. */
public final class BossTest {
    public static int requestedDepth;
    public static boolean launchPending;
    public static Boolean requestedFast;
    public static boolean automatic, stronger, crowded;
    private static int slot, steps, jumps, previousPos = -1;
    private static long started, lastStep, lastLog, lastReady;
    private static boolean entered, seenBoss, filled, postFloor;
    private static boolean manualEntryPending;

    public static boolean immortal() {
        return DeviceCompat.isDebug() && SPDSettings.bossTestGod();
    }

    public static void start(int depth, boolean auto, boolean strong, boolean crowd) {
        if (!DeviceCompat.isDebug() || (depth != 10 && depth != 20)) return;
        {
            int savedSlot = slot > 0 ? slot : SPDSettings.bossTestSlot();
            slot = 0;
            try {
                if (savedSlot > 0 && com.watabou.utils.FileUtils.bundleFromFile(GamesInProgress.gameFile(savedSlot))
                        .getBundle("hero").getBoolean("boss_test_run")) slot = savedSlot;
            } catch (java.io.IOException ignored) { }
            if (slot == 0) slot = GamesInProgress.firstEmpty();
        }
        if (slot < 1) {
            Game.scene().add(new WndMessage("测试需要一个空存档槽；不会覆盖已有存档。"));
            slot = 0;
            return;
        }
        requestedDepth = depth;
        automatic = auto;
        stronger = strong;
        crowded = crowd;
        SPDSettings.bossTestGod(true);
        SPDSettings.bossTestSlot(slot);
        GamesInProgress.curSlot = slot;
        GamesInProgress.selectedClass = HeroClass.WARRIOR;
        InterlevelScene.mode = InterlevelScene.Mode.BOSS_TEST;
        Game.switchScene(InterlevelScene.class);
    }

    public static void generate() {
        if (!DeviceCompat.isDebug()) throw new IllegalStateException("Debug build required");
        Modifiers saved = SPDSettings.modifiers();
        Modifiers test = new Modifiers();
        enable(test, Challenges.GRINDING_3);
        if (stronger) enable(test, Challenges.STRONGER_BOSSES);
        if (crowded) enable(test, Challenges.INFINITY_MOBS);
        SPDSettings.modifiers(test);
        try { Dungeon.init(); } finally { SPDSettings.modifiers(saved); }
        Dungeon.depth = requestedDepth - 1;
        Dungeon.hero.HT = Dungeon.hero.HP = 500;
        Dungeon.hero.bossTestRun = true;
        new com.shatteredpixel.shatteredpixeldungeon.items.scrolls.ScrollOfUpgrade()
                .quantity(100000).identify().collect();
        Level level = Dungeon.newLevel();
        Dungeon.switchLevel(level, level.entrance);
        entered = seenBoss = filled = postFloor = false;
        manualEntryPending = !automatic;
        steps = jumps = 0;
        previousPos = -1;
        started = lastReady = System.nanoTime();
        lastStep = lastLog = 0;
        log("START depth=" + Dungeon.depth + " auto=" + automatic + " strong=" + stronger
                + " crowded=" + crowded + " fast=" + SPDSettings.fastAnimations() + " slot=" + slot);
    }

    private static void enable(Modifiers mods, Challenges challenge) {
        for (Challenges req : mods.recursiveRequirements(challenge)) mods.challenges[req.id] = true;
        mods.challenges[challenge.id] = true;
    }

    public static void update() {
        if (!DeviceCompat.isDebug() || Dungeon.hero == null) return;
        if (!automatic) {
            if (manualEntryPending && Dungeon.hero.ready) {
                manualEntryPending = false;
                if (Dungeon.level instanceof PrisonBossLevel) ((PrisonBossLevel) Dungeon.level).progress();
                else if (Dungeon.level instanceof CityBossLevel) Dungeon.level.seal();
                for (Mob mob : Dungeon.level.mobs()) {
                    if (mob instanceof Tengu || mob instanceof DwarfKing) {
                        placeHeroNear(mob);
                        log("MANUAL_READY depth=" + Dungeon.depth + " god=" + immortal()
                                + " bossHP=" + mob.HP + " upgrades=" + Dungeon.hero.belongings
                                .getItem(com.shatteredpixel.shatteredpixeldungeon.items.scrolls.ScrollOfUpgrade.class).quantity());
                        break;
                    }
                }
            }
            return;
        }
        long now = System.nanoTime();
        if (postFloor) {
            if (Dungeon.depth != requestedDepth + 1 || !Dungeon.hero.ready) return;
            log("PASS_NEXT_FLOOR depth=" + Dungeon.depth + " heroAlive=" + Dungeon.hero.isAlive());
            automatic = false;
            return;
        }
        if ((now - started) > 180_000_000_000L) {
            log("FAIL timeout depth=" + Dungeon.depth + " ready=" + Dungeon.hero.ready);
            automatic = false;
            GameScene.logActorThread = true;
            return;
        }
        Mob boss = null;
        for (Mob mob : Dungeon.level.mobs()) {
            if (mob instanceof Tengu || mob instanceof DwarfKing) { boss = mob; break; }
        }
        if (boss != null && Dungeon.hero.ready) {
            if (!seenBoss) {
                placeHeroNear(boss);
            }
            seenBoss = true;
            if (boss instanceof Tengu && previousPos != -1 && previousPos != boss.pos()) jumps++;
            previousPos = boss.pos();
            if (!boss.sprite.isMoving) {
                PointF expected = boss.sprite.worldToCamera(boss.pos());
                if (Math.abs(expected.x - boss.sprite.x) > .1f || Math.abs(expected.y - boss.sprite.y) > .1f) {
                    log("FAIL spritePosition logical=" + boss.pos() + " visual=" + boss.sprite.x + "," + boss.sprite.y
                            + " expected=" + expected.x + "," + expected.y);
                    automatic = false;
                    return;
                }
            }
        }
        if (now - lastLog > 1_000_000_000L) {
            lastLog = now;
            log("STATE depth=" + Dungeon.depth + " steps=" + steps + " ready=" + Dungeon.hero.ready
                    + " hp=" + Dungeon.hero.HP + " locked=" + Dungeon.level.locked
                    + (boss == null ? " boss=none" : " boss=" + boss.getClass().getSimpleName()
                    + " bossHP=" + boss.HP + " HT=" + boss.HT + " shield=" + boss.shielding()));
        }
        if (!Dungeon.hero.ready) {
            if (now - lastReady > 15_000_000_000L) {
                log("FAIL turnStall depth=" + Dungeon.depth);
                automatic = false;
                GameScene.logActorThread = true;
            }
            return;
        }
        lastReady = now;
        if (now - lastStep < 250_000_000L) return;
        lastStep = now;
        if (!entered) {
            entered = true;
            if (Dungeon.level instanceof PrisonBossLevel) ((PrisonBossLevel) Dungeon.level).progress();
            else if (Dungeon.level instanceof CityBossLevel) Dungeon.level.seal();
            Dungeon.hero.spendAndNext(1f);
            return;
        }
        if (Dungeon.level instanceof PrisonBossLevel
                && ((PrisonBossLevel) Dungeon.level).state() == PrisonBossLevel.State.FIGHT_PAUSE) {
            ((PrisonBossLevel) Dungeon.level).progress();
            // Normal play enters the arena on foot. The automated test skips that walk,
            // so move its hero into the new arena before attacking or advancing time.
            for (Mob mob : Dungeon.level.mobs()) {
                if (mob instanceof Tengu) {
                    placeHeroNear(mob);
                    log("ARENA_READY heroPos=" + Dungeon.hero.pos() + " bossPos=" + mob.pos()
                            + " passable=" + Dungeon.level.passable[Dungeon.hero.pos()]
                            + " visible=" + Dungeon.hero.fieldOfView[mob.pos()]);
                    break;
                }
            }
            Dungeon.hero.spendAndNext(1f);
            return;
        }
        if (seenBoss && boss == null && !Dungeon.level.locked) {
            log("PASS_BOSS depth=" + Dungeon.depth + " steps=" + steps + " jumps=" + jumps
                    + " unlocked=true heroAlive=" + Dungeon.hero.isAlive());
            for (Mob mob : Dungeon.level.mobs().toArray(new Mob[0])) {
                if (mob.alignment == Char.Alignment.NEUTRAL) {
                    mob.destroy();
                    mob.sprite.killAndErase();
                }
            }
            // This stress modifier would fill the next normal floor. The post-boss transition
            // checks passage and loading independently of that unrelated spawn stress.
            Dungeon.modifiers.challenges[Challenges.INFINITY_MOBS.id] = false;
            postFloor = true;
            InterlevelScene.mode = InterlevelScene.Mode.DESCEND;
            Game.switchScene(InterlevelScene.class);
            return;
        }
        if (crowded && !filled && boss instanceof DwarfKing && boss.shielding() > 0) {
            filled = true;
            int count = 0;
            for (int cell = 0; cell < Dungeon.level.length(); cell++) {
                if (!Dungeon.level.passable[cell] || Actor.findChar(cell) != null) continue;
                Rat blocker = new Rat();
                blocker.alignment = Char.Alignment.NEUTRAL;
                blocker.state = blocker.PASSIVE;
                blocker.pos(cell);
                GameScene.add(blocker);
                count++;
            }
            log("CROWDED filled=" + count);
        }
        // Kill actual summoned enemies through damage, so KingDamager and wave transitions run.
        for (Mob mob : Dungeon.level.mobs().toArray(new Mob[0])) {
            if (mob != boss && mob.alignment == Char.Alignment.ENEMY) mob.damage(100_000_000, Dungeon.hero);
        }
        steps++;
        if (boss != null && boss.shielding() == 0) {
            final Mob target = boss;
            Dungeon.hero.busy();
            Dungeon.hero.sprite.attack(target.pos(), () -> {
                Dungeon.hero.attack(target, 1f, Math.max(1, target.HT / 8f), 1_000_000f);
                Dungeon.hero.spendAndNext(1f);
            });
        } else Dungeon.hero.spendAndNext(1f);
    }

    private static void placeHeroNear(Mob boss) {
        for (int offset : com.watabou.utils.PathFinder.NEIGHBOURS8) {
            int cell = boss.pos() + offset;
            if (cell < 0 || cell >= Dungeon.level.length() || !Dungeon.level.passable[cell]
                    || Actor.findChar(cell) != null) continue;
            Dungeon.hero.pos(cell);
            Dungeon.hero.sprite.place(cell);
            Dungeon.observe();
            com.watabou.noosa.Camera.main.snapTo(Dungeon.hero.sprite.center());
            break;
        }
    }
    private static void log(String message) { DeviceCompat.log("BossTest", message); }
    private BossTest() {}
}

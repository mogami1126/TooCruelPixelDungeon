/*
 * Pixel Dungeon
 * Copyright (C) 2012-2015 Oleg Dolya
 *
 * Shattered Pixel Dungeon
 * Copyright (C) 2014-2021 Evan Debenham
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>
 */

package com.shatteredpixel.shatteredpixeldungeon.actors;

import com.shatteredpixel.shatteredpixeldungeon.Dungeon;
import com.shatteredpixel.shatteredpixeldungeon.Statistics;
import com.shatteredpixel.shatteredpixeldungeon.actors.blobs.Blob;
import com.shatteredpixel.shatteredpixeldungeon.actors.buffs.Buff;
import com.shatteredpixel.shatteredpixeldungeon.actors.mobs.Mob;
import com.watabou.utils.Bundlable;
import com.shatteredpixel.shatteredpixeldungeon.utils.TurnTime;
import com.watabou.utils.DeviceCompat;
import com.watabou.utils.Bundle;
import com.watabou.utils.SparseArray;

import java.util.HashMap;
import java.util.HashSet;

public abstract class Actor implements Bundlable {
	
	public static final float TICK	= 1f;

	private volatile long time;
    private int stalledActions;
    private boolean reportedTimeRepair;

	protected float getTime() {
		return TurnTime.turns(time);
	}

	private int id = 0;

	//default priority values for general actor categories
	//note that some specific actors pick more specific values
	//e.g. a buff acting after all normal buffs might have priority BUFF_PRIO + 1
	protected static final int VFX_PRIO    = 100;   //visual effects take priority
	protected static final int HERO_PRIO   = 0;     //positive is before hero, negative after
	protected static final int BLOB_PRIO   = -10;   //blobs act after hero, before mobs
	protected static final int MOB_PRIO    = -20;   //mobs act between buffs and blobs
	protected static final int BUFF_PRIO   = -30;   //buffs act last in a turn
	private static final int   DEFAULT     = -100;  //if no priority is given, act after all else

	//used to determine what order actors act in if their time is equal. Higher values act earlier.
	protected int actPriority = DEFAULT;

	protected abstract boolean act();
	
    protected void spend(float turns) {
        time=TurnTime.add(time,TurnTime.delta(turns));
    }
    public void spendToWhole(){
        if(time!=TurnTime.INACTIVE){
            long floor=TurnTime.whole(time);
            time=time==floor?time:TurnTime.add(floor,TurnTime.UNITS);
        }
    }
    protected void postpone(float turns){
        if(time!=TurnTime.INACTIVE) time=Math.max(time,TurnTime.add(now,TurnTime.delta(turns)));
    }
    public float cooldown(){return TurnTime.turns(time==TurnTime.INACTIVE?time:time-now);}
    public void clearTime(){time=0;stalledActions=0;}
    protected void diactivate(){time=TurnTime.INACTIVE;}

	protected void onAdd() {}
	
	protected void onRemove() {}

	private static final String TIME    = "time";
	private static final String ID      = "id";

	@Override
	public void storeInBundle( Bundle bundle ) {
		bundle.put( TIME, TurnTime.turns(time) );
        bundle.put("time_ticks_v1", time);
		bundle.put( ID, id );
	}

	@Override
	public void restoreFromBundle( Bundle bundle ) {
		time = bundle.contains("time_ticks_v1") ? bundle.getLong("time_ticks_v1") : TurnTime.legacy(bundle.getFloat(TIME));
		int incomingID = bundle.getInt( ID );
		if (Actor.findById(incomingID) == null){
			id = incomingID;
		} else {
			id = nextID++;
		}
	}

	public int id() {
		if (id > 0) {
			return id;
		} else {
			return (id = nextID++);
		}
	}

	// **********************
	// *** Static members ***
	// **********************
	
	private static HashSet<Actor> all = new HashSet<>();
	private static HashSet<Char> chars = new HashSet<>();
	private static HashSet<Char> dispositionedChars = new HashSet<>();
	private static HashMap<Integer,Char> charsPositioned = new HashMap<>();
	private static volatile Actor current;
	private static volatile Char waitingForMotion;
	private static volatile long motionWaitStarted;
	private static volatile boolean motionRecoveryAttempted;

	// Render-thread entry point: release one stalled visual wait, never replay an attack.
	public static boolean recoverStalledMotion(boolean manual) {
		Char ch = waitingForMotion;
		if (ch == null || ch.sprite == null) return false;
		synchronized (ch.sprite) {
			if (waitingForMotion != ch || !ch.sprite.isMoving || motionRecoveryAttempted
					|| (!manual && System.nanoTime() - motionWaitStarted < 10_000_000_000L)) {
				return false;
			}
			motionRecoveryAttempted = true;
			ch.sprite.recoverMotion();
			return true;
		}
	}

	private static SparseArray<Actor> ids = new SparseArray<>();
	private static int nextID = 1;

	private static volatile long now = 0;
	
	public static float now(){
		return TurnTime.turns(now);
	}
	
	public static synchronized void clear() {
		
		now = 0;

		all.clear();
		chars.clear();

		dispositionedChars.clear();
		charsPositioned.clear();

		ids.clear();
	}

	public static synchronized void fixTime() {
		
		if (all.isEmpty()) return;
		
		long min = TurnTime.INACTIVE;
		for (Actor a : all) {
			if (a.time < min) {
				min = a.time;
			}
		}

		//Only pull everything back by whole numbers
		//So that turns always align with a whole number
		if(min==TurnTime.INACTIVE) return;
        min=TurnTime.whole(min);
		for (Actor a : all) {
			if(a.time!=TurnTime.INACTIVE) a.time -= min;
		}

		if (Dungeon.hero != null && all.contains( Dungeon.hero )) {
			Statistics.duration += TurnTime.turns(min);
		}
		now -= min;
	}
	
	public static void init() {
		
		add( Dungeon.hero );
		
		for (Mob mob : Dungeon.level.mobs()) {
			add( mob );
		}
		
		for (Blob blob : Dungeon.level.blobs.values()) {
			add( blob );
		}
		for (LevelObject obj : Dungeon.level.objects) {
			add( obj );
		}
		
		current = null;
	}

	private static final String NEXTID = "nextid";

	public static void storeNextID( Bundle bundle){
		bundle.put( NEXTID, nextID );
	}

	public static void restoreNextID( Bundle bundle){
		nextID = bundle.getInt( NEXTID );
	}

	public static void resetNextID(){
		nextID = 1;
	}

	/*protected*/public void next() {
		if (current == this) {
			current = null;
		}
	}

	public static boolean processing(){
		return current != null;
	}

	public static int curActorPriority() {
		return current != null ? current.actPriority : DEFAULT;
	}
	
	public static volatile boolean keepActorThreadAlive = true;
	
	public static void process() {
		
		boolean doNext;
		boolean interrupted = false;
        int sliceActions=0;
        long sliceStarted=System.nanoTime();

		do {
			if (dispositionedChars.size() > 0) {
				Char[] toRemove = new Char[dispositionedChars.size()];
				int i = 0;
				for (Char ch : dispositionedChars) {
					if (!chars.contains(ch)) {
						toRemove[i] = ch;
						i++;
						continue;
					}
					Char old = findChar(ch.pos());
					if (old == null || !chars.contains(old)) {
						charsPositioned.put(ch.pos(), ch);
						toRemove[i] = ch;
						i++;
						continue;
					}
				}

				for (i -= 1; i >= 0; i--) {
					dispositionedChars.remove(toRemove[i]);
				}
			}

			if(Dungeon.level != null) {
				Dungeon.level.fixDispositionedMobs();
			}

			current = null;
			if (!interrupted) {
				long earliest = TurnTime.INACTIVE;

				synchronized(Actor.class) {
                for (Actor actor : all) {
                    if(actor.time==TurnTime.INACTIVE) continue;
					
					//some actors will always go before others if time is equal.
					if (actor.time < earliest ||
							actor.time == earliest && (current == null || (actor.actPriority > current.actPriority || (actor.actPriority == current.actPriority && actor.id() < current.id())))) {
						earliest = actor.time;
						current = actor;
					}
					
				}
				}
			}

			if  (current != null) {

				now = current.time;
				Actor acting = current;

				if (acting instanceof Char && ((Char) acting).sprite != null) {
					// If it's character's turn to act, but its sprite
					// is moving, wait till the movement is over
					try {
						synchronized (((Char)acting).sprite) {
							if (((Char)acting).sprite.isMoving) {
								waitingForMotion = (Char) acting;
								motionWaitStarted = System.nanoTime();
								motionRecoveryAttempted = false;
								try {
									while (((Char) acting).sprite.isMoving) {
										((Char) acting).sprite.wait();
									}
								} finally {
									waitingForMotion = null;
								}
							}
						}
					} catch (InterruptedException e) {
						interrupted = true;
					}
				}
				
				interrupted = interrupted || Thread.interrupted();
				
				if (interrupted){
					doNext = false;
					current = null;
				} else {
					long before=acting.time;
                    doNext = acting.act();
                    // Only continuing, still registered actors can monopolize a timestamp.
                    // Allow short same-time callback chains; never replay their action.
                    if(doNext && all.contains(acting) && acting.time!=TurnTime.INACTIVE && acting.time<=before){
                        if(++acting.stalledActions>=32){
                            acting.time=TurnTime.add(Math.max(now,acting.time),TurnTime.MIN_ACTION);
                            acting.stalledActions=0;
                            if(!acting.reportedTimeRepair){
                                acting.reportedTimeRepair=true;
                                DeviceCompat.log("TurnGuard", "non-progress actor="+acting.getClass().getName()+" id="+acting.id());
                            }
                        }
                    }else acting.stalledActions=0;
                    if(++sliceActions>=128 || System.nanoTime()-sliceStarted>=4_000_000L){
                        try{Thread.sleep(1);}catch(InterruptedException e){interrupted=true;}
                        sliceActions=0; sliceStarted=System.nanoTime();
                    }
					if (doNext && (Dungeon.hero == null || !Dungeon.hero.isAlive())) {
						doNext = false;
						current = null;
					}
				}
			} else {
				doNext = false;
			}

			if (!doNext){
				synchronized (Thread.currentThread()) {
					
					interrupted = interrupted || Thread.interrupted();
					
					if (interrupted){
						current = null;
						interrupted = false;
					}

					//signals to the gamescene that actor processing is finished for now
					Thread.currentThread().notify();
					
					try {
						Thread.currentThread().wait();
					} catch (InterruptedException e) {
						interrupted = true;
					}
				}
			}

		} while (keepActorThreadAlive);
	}
	
	public static void add( Actor actor ) {
		add( actor, now );
	}
	
	public static void addDelayed( Actor actor, float delay ) {
		add(actor,TurnTime.add(now,TurnTime.delta(delay)));
	}
	
	private static synchronized void add( Actor actor, long time ) {
		
		if (all.contains( actor )) {
			return;
		}

		ids.put( actor.id(),  actor );

		all.add( actor );
		actor.time = TurnTime.add(actor.time,time);
		actor.onAdd();
		
		if (actor instanceof Char) {
			Char ch = (Char)actor;
			Char oldChar = charsPositioned.get(ch.pos());
			if (oldChar != null && chars.contains(oldChar)) {
				dispositionedChars.add(oldChar);
			}
			dispositionedChars.remove(ch);
			charsPositioned.put( ch.pos(), ch );
			chars.add( ch );
			for (Buff buff : ch.buffs()) {
				add(buff);
			}
		}
	}

	public static synchronized void move(Char ch, int oldPos, int newPos) {
		if (!chars.contains(ch)) return;
		charsPositioned.remove(oldPos);
		Char oldChar = charsPositioned.get(newPos);
		if (oldChar != null && chars.contains(oldChar)) {
			dispositionedChars.add(oldChar);
		}
		dispositionedChars.remove(ch);
		charsPositioned.put(newPos, ch);
	}
	
	public static synchronized void remove( Actor actor ) {
		if (actor != null) {
			all.remove( actor );
			if (actor instanceof Char) {
				if (charsPositioned.get(((Char) actor).pos()) == actor)
					charsPositioned.remove(((Char) actor).pos());
				chars.remove(actor);
				dispositionedChars.remove(actor);
			}
			actor.onRemove();

			if (actor.id > 0) {
				ids.remove( actor.id );
			}
		}
	}

	public static synchronized Class<? extends Actor> getCurrentActorClass() {
		return current == null ? null : current.getClass();
	}

	public static synchronized Char findChar(int pos) {
		return charsPositioned.get(pos);
	}

	public static synchronized Actor findById( int id ) {
		return ids.get( id );
	}

	public static synchronized HashSet<Actor> all() {
		return new HashSet<>(all);
	}

	public static synchronized HashSet<Char> chars() { return chars; }

	public static synchronized HashMap<Integer, Char> charsPositioned() { return charsPositioned; }
}

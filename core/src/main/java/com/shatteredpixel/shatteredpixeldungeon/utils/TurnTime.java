package com.shatteredpixel.shatteredpixeldungeon.utils;

/** Fixed point scheduler time, separate from health/damage magnitudes. */
public final class TurnTime {
    public static final long UNITS=1L<<20;
    public static final long INACTIVE=Long.MAX_VALUE;
    public static final long MIN_ACTION=UNITS/64;
    private static final long MAX_DELAY=UNITS*1_000_000L;
    public static long delta(float turns) {
        if(Float.isNaN(turns)) return MIN_ACTION;
        if(turns==Float.POSITIVE_INFINITY) return UNITS;
        if(turns==Float.NEGATIVE_INFINITY) return 0;
        if(turns==0) return 0; // refunds and same-time events remain legitimate
        double units=(double)turns*UNITS;
        long rounded=Math.round(Math.max(-MAX_DELAY,Math.min(MAX_DELAY,units)));
        return rounded==0?(turns>0?1:-1):rounded;
    }
    public static long add(long current,long delta) {
        if(current==INACTIVE) return INACTIVE;
        long limit=Long.MAX_VALUE-1;
        if(delta>0 && current>limit-delta) return limit;
        if(delta<0 && current<Long.MIN_VALUE-delta) return Long.MIN_VALUE;
        return current+delta;
    }
    public static float turns(long units){return units==INACTIVE?Float.MAX_VALUE:(float)((double)units/UNITS);}
    public static long legacy(float turns){return turns==Float.MAX_VALUE?INACTIVE:delta(turns);}
    public static long whole(long units){return Math.floorDiv(units,UNITS)*UNITS;}
    private TurnTime(){}
}

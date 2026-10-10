package com.shatteredpixel.shatteredpixeldungeon.utils;

/** Saturating health arithmetic while saves and combat still use signed 32-bit integers. */
public final class HealthMath {
    public static int maximum(double value) {
        if (Double.isNaN(value) || value < 1) return 1;
        return (int)Math.min(Integer.MAX_VALUE, Math.floor(value + .5d));
    }

    public static int heal(int hp, int ht, long amount) {
        return (int)Math.min(Math.max(0, ht), (long)hp + Math.max(0L, amount));
    }

    public static int reserve(int current, int extra) {
        return (int)Math.min(Integer.MAX_VALUE, (long)Math.max(0, current) + Math.max(0, extra));
    }

    private HealthMath() {}
}

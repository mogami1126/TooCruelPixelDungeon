package com.shatteredpixel.shatteredpixeldungeon.utils;
import com.watabou.utils.Bundle;

/** Nonnegative scientific magnitude with fixed precision; never holds NaN or infinity. */
public final class Magnitude implements Comparable<Magnitude> {
    public static final Magnitude ZERO = new Magnitude(0, 0);
    public static final Magnitude ONE = new Magnitude(1, 0);
    private final double mantissa;
    private final long exponent;
    private Magnitude(double mantissa, long exponent) { this.mantissa=mantissa; this.exponent=exponent; }
    public static Magnitude of(double value) {
        if (!Double.isFinite(value) || value < 0) throw new IllegalArgumentException("Invalid magnitude");
        if (value==0) return ZERO;
        long e=(long)Math.floor(Math.log10(value));
        // Scaling subnormal doubles by a positive power avoids pow(10,-324) underflow.
        double m=e < -300 ? value * 1e300 / Math.pow(10,e+300) : value/Math.pow(10,e);
        return normalized(m,e);
    }
    public static Magnitude scientific(double mantissa, long exponent) {
        if (!Double.isFinite(mantissa) || mantissa < 0) throw new IllegalArgumentException("Invalid mantissa");
        return normalized(mantissa,exponent);
    }
    private static Magnitude normalized(double m,long e) {
        if (m==0) return ZERO;
        while(m>=10) { m/=10; e=Math.addExact(e,1); }
        while(m<1) { m*=10; e=Math.subtractExact(e,1); }
        return new Magnitude(m,e);
    }
    public static Magnitude power(double base,double bonus) {
        if (!Double.isFinite(base) || base<=0 || !Double.isFinite(bonus)) throw new IllegalArgumentException("Invalid power");
        double log=Math.log10(base)*bonus;
        if(!Double.isFinite(log) || log <= Long.MIN_VALUE || log >= Long.MAX_VALUE) throw new ArithmeticException("Exponent outside range");
        long e=(long)Math.floor(log);
        return normalized(Math.pow(10,log-e),e);
    }
    public Magnitude multiply(Magnitude other) {
        if(mantissa==0 || other.mantissa==0) return ZERO;
        return normalized(mantissa*other.mantissa,Math.addExact(exponent,other.exponent));
    }
    public Magnitude add(Magnitude other) {
        if(mantissa==0) return other;
        if(other.mantissa==0) return this;
        Magnitude high=exponent>=other.exponent?this:other, low=high==this?other:this;
        if ((double)high.exponent-(double)low.exponent>16) return high;
        return normalized(high.mantissa+low.mantissa*Math.pow(10,low.exponent-high.exponent),high.exponent);
    }
    /** Nonnegative subtraction. A lethal subtraction is exactly zero, never forced to one. */
    public Magnitude subtract(Magnitude other) {
        if(compareTo(other)<=0) return ZERO;
        if(other.mantissa==0 || (double)exponent-(double)other.exponent>16) return this;
        return normalized(mantissa-other.mantissa*Math.pow(10,other.exponent-exponent),exponent);
    }
    public int compareTo(Magnitude other) {
        if(mantissa==0 || other.mantissa==0) return Double.compare(mantissa,other.mantissa);
        int e=Long.compare(exponent,other.exponent);
        return e!=0?e:Double.compare(mantissa,other.mantissa);
    }
    /** Explicit compatibility boundary while older stat fields still use float. */
    public float finiteFloat() {
        if(mantissa==0) return 0;
        if(exponent>38) return Float.MAX_VALUE;
        if(exponent< -45) return 0;
        return (float)Math.min(Float.MAX_VALUE,mantissa*Math.pow(10,exponent));
    }
    public double mantissa(){return mantissa;}
    public long exponent(){return exponent;}
    public void store(Bundle parent,String key){
        Bundle data=new Bundle();
        data.put("mantissa",Double.toString(mantissa));
        data.put("exponent",exponent);
        parent.put(key,data);
    }
    public static Magnitude restore(Bundle parent,String key){
        Bundle data=parent.getBundle(key);
        return scientific(Double.parseDouble(data.getString("mantissa")),data.getLong("exponent"));
    }
    public String toString(){return mantissa+"e"+exponent;}
}

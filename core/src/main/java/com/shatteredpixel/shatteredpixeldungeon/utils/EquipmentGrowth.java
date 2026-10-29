package com.shatteredpixel.shatteredpixeldungeon.utils;

public final class EquipmentGrowth {
    public static Magnitude magnitude(double base,double bonus){return Magnitude.power(base,bonus);}
    public static float multiplier(double base,double bonus){return magnitude(base,bonus).finiteFloat();}
    /** Preserve the early curve; smoothly approach 64 actions/turn instead of zero cost. */
    public static float speed(double base,double bonus){
        double log=Math.log(base)*bonus;
        double sign=log<0?-1:1;
        double a=Math.abs(log), knee=Math.log(8);
        double value=a<=knee?Math.exp(a):8+56*(-Math.expm1(-(a-knee)/7));
        return (float)(sign<0?1/value:value);
    }
    /** Charging is capacity limited, so rates above this are settled directly. */
    public static float charge(double base,double bonus){return Math.max(1f/1024,Math.min(1024,multiplier(base,bonus)));}
    public static String percentIncrease(double base,double bonus){
        Magnitude value=magnitude(base,bonus);
        if(value.compareTo(Magnitude.ONE)<0) return new java.text.DecimalFormat("#.##").format(100d*(value.finiteFloat()-1));
        Magnitude percent=value.subtract(Magnitude.ONE).multiply(Magnitude.of(100));
        return percent.exponent()>6 ? new java.text.DecimalFormat("#.###").format(percent.mantissa())+"e"+percent.exponent()
                : new java.text.DecimalFormat("#.##").format(percent.finiteFloat());
    }
    private EquipmentGrowth(){}
}

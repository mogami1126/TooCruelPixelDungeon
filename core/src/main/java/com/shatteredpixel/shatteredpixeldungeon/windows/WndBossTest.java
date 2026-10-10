package com.shatteredpixel.shatteredpixeldungeon.windows;

import com.shatteredpixel.shatteredpixeldungeon.SPDSettings;
import com.shatteredpixel.shatteredpixeldungeon.ui.RedButton;
import com.shatteredpixel.shatteredpixeldungeon.ui.Window;
import com.shatteredpixel.shatteredpixeldungeon.utils.BossTest;
import com.watabou.utils.DeviceCompat;

public class WndBossTest extends Window {
    private int y;
    public WndBossTest() {
        if (!DeviceCompat.isDebug()) { hide(); return; }
        button("不死：" + (SPDSettings.bossTestGod() ? "开启" : "关闭"), () -> {
            SPDSettings.bossTestGod(!SPDSettings.bossTestGod()); hide();
        });
        button("快速动画：" + (SPDSettings.fastAnimations() ? "开启" : "关闭"), () -> {
            SPDSettings.fastAnimations(!SPDSettings.fastAnimations()); hide();
        });
        button("直达天狗（MMO / 不死）", () -> BossTest.start(10, false, false, false));
        button("直达国王（MMO / 不死）", () -> BossTest.start(20, false, false, false));
        button("自动验证天狗", () -> BossTest.start(10, true, false, false));
        button("自动验证国王", () -> BossTest.start(20, true, false, false));
        button("国王满场压力测试", () -> BossTest.start(20, true, true, true));
        button("停止自动验证", () -> { BossTest.automatic = false; hide(); });
        resize(160, y);
    }
    private void button(String text, Runnable action) {
        RedButton btn = new RedButton(text) {
            @Override protected void onClick() { hide(); action.run(); }
        };
        add(btn); btn.setRect(0, y, 160, 20); y += 22;
    }
}

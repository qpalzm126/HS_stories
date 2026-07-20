package com.hsstory.hs_story_app

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.net.Uri
import android.widget.RemoteViews
import es.antonborri.home_widget.HomeWidgetLaunchIntent
import es.antonborri.home_widget.HomeWidgetProvider
import org.json.JSONArray

/**
 * 聖靈故事 Android 桌面 Widget。
 *
 * 資料來源：Flutter 端 home_widget 寫入的 SharedPreferences。
 *  - hs_articles：最新 N 篇的 JSON 陣列（title/excerpt/url/slug/date）— 左右切換用。
 *  - hs_index   ：目前顯示第幾篇（widget 端狀態，切換時更新）。
 *
 * 互動：
 *  - 整塊點擊    → ACTION_VIEW 開啟該篇文章網址。
 *  - ◀ / ▶ 鍵   → 廣播給自己，切換 index 後重繪（純 widget、離線）。
 *  - 🔊 朗讀 鍵  → 開啟 App 到該篇（hsstory://speak?slug=…）並自動朗讀全文。
 */
class HSStoryWidgetProvider : HomeWidgetProvider() {

    companion object {
        private const val PREFS = "HomeWidgetPreferences" // home_widget 外掛使用的 prefs 名
        private const val KEY_ARTICLES = "hs_articles"
        private const val KEY_INDEX = "hs_index"
        const val ACTION_PREV = "com.hsstory.hs_story_app.WIDGET_PREV"
        const val ACTION_NEXT = "com.hsstory.hs_story_app.WIDGET_NEXT"
    }

    override fun onUpdate(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetIds: IntArray,
        widgetData: SharedPreferences
    ) {
        val articles = parseArticles(widgetData)
        val index = clamp(widgetData.getInt(KEY_INDEX, 0), articles.length())
        appWidgetIds.forEach { widgetId ->
            appWidgetManager.updateAppWidget(
                widgetId, buildViews(context, articles, index, widgetId)
            )
        }
    }

    override fun onReceive(context: Context, intent: Intent) {
        when (intent.action) {
            ACTION_PREV -> shift(context, -1)
            ACTION_NEXT -> shift(context, +1)
        }
        super.onReceive(context, intent) // 讓 home_widget / AppWidget 既有流程照跑
    }

    private fun prefs(context: Context): SharedPreferences =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    private fun parseArticles(data: SharedPreferences): JSONArray {
        val raw = data.getString(KEY_ARTICLES, null) ?: return JSONArray()
        return try {
            JSONArray(raw)
        } catch (e: Exception) {
            JSONArray()
        }
    }

    private fun clamp(i: Int, count: Int): Int =
        if (count <= 0) 0 else i.coerceIn(0, count - 1)

    /** 切換目前故事（循環），更新 index 後重繪所有 widget。 */
    private fun shift(context: Context, delta: Int) {
        val data = prefs(context)
        val count = parseArticles(data).length()
        if (count == 0) return
        val cur = clamp(data.getInt(KEY_INDEX, 0), count)
        val next = (cur + delta + count) % count
        data.edit().putInt(KEY_INDEX, next).apply()

        val mgr = AppWidgetManager.getInstance(context)
        val ids = mgr.getAppWidgetIds(
            ComponentName(context, HSStoryWidgetProvider::class.java)
        )
        val articles = parseArticles(data)
        ids.forEach { id -> mgr.updateAppWidget(id, buildViews(context, articles, next, id)) }
    }

    private fun buildViews(
        context: Context,
        articles: JSONArray,
        index: Int,
        widgetId: Int
    ): RemoteViews {
        val views = RemoteViews(context.packageName, R.layout.hs_story_widget)

        if (articles.length() == 0) {
            views.setTextViewText(R.id.widget_title, "聖靈故事")
            views.setTextViewText(R.id.widget_excerpt, "開啟 App 載入最新故事")
            views.setTextViewText(R.id.widget_pos, "")
            views.setOnClickPendingIntent(
                R.id.widget_root,
                HomeWidgetLaunchIntent.getActivity(context, MainActivity::class.java)
            )
            return views
        }

        val a = articles.getJSONObject(index)
        views.setTextViewText(R.id.widget_title, a.optString("title", "聖靈故事"))
        views.setTextViewText(R.id.widget_excerpt, a.optString("excerpt", ""))
        views.setTextViewText(R.id.widget_pos, "${index + 1}/${articles.length()}")

        // 整塊點擊 → 開文章網址
        val url = a.optString("url", "")
        if (url.isNotEmpty()) {
            val view = Intent(Intent.ACTION_VIEW, Uri.parse(url))
            val flags = PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            views.setOnClickPendingIntent(
                R.id.widget_root,
                PendingIntent.getActivity(context, 100 + widgetId, view, flags)
            )
        }

        views.setOnClickPendingIntent(R.id.widget_prev, broadcast(context, ACTION_PREV, 1))
        views.setOnClickPendingIntent(R.id.widget_next, broadcast(context, ACTION_NEXT, 2))

        // 🔊 → 開 App 到該篇並自動朗讀
        val slug = a.optString("slug", "")
        val speakUri = Uri.parse("hsstory://speak?slug=" + Uri.encode(slug))
        views.setOnClickPendingIntent(
            R.id.widget_speak,
            HomeWidgetLaunchIntent.getActivity(context, MainActivity::class.java, speakUri)
        )
        return views
    }

    private fun broadcast(context: Context, action: String, req: Int): PendingIntent {
        val intent = Intent(context, HSStoryWidgetProvider::class.java).setAction(action)
        val flags = PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        return PendingIntent.getBroadcast(context, req, intent, flags)
    }
}

package com.hsstory.hs_story_app

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.net.Uri
import android.os.Build
import android.view.View
import android.widget.RemoteViews
import es.antonborri.home_widget.HomeWidgetProvider
import org.json.JSONArray

/**
 * 聖靈故事 Android 桌面 Widget。
 *
 * 資料來源：Flutter 端 home_widget 寫入的 SharedPreferences。
 *  - hs_articles：最新 N 篇 JSON（title/excerpt/body/url/slug/date）— 左右切換 + 顯示全文用。
 *  - hs_index   ：目前顯示第幾篇（widget 端狀態，切換時更新）。
 *
 * 互動：
 *  - 整塊點擊 → ACTION_VIEW 開啟該篇文章網址。
 *  - ◀ / ▶   → 廣播給自己，切換 index 後重繪（純 widget、離線）。
 * 內文顯示該篇全文（去 Markdown）；API 31+ 可在 widget 內捲動。
 */
class HSStoryWidgetProvider : HomeWidgetProvider() {

    companion object {
        private const val PREFS = "HomeWidgetPreferences"
        private const val KEY_ARTICLES = "hs_articles"
        private const val KEY_INDEX = "hs_index"
        const val ACTION_PREV = "com.hsstory.hs_story_app.WIDGET_PREV"
        const val ACTION_NEXT = "com.hsstory.hs_story_app.WIDGET_NEXT"
        private const val LAUNCH_ACTION = "es.antonborri.home_widget.action.LAUNCH"
    }

    override fun onUpdate(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetIds: IntArray,
        widgetData: SharedPreferences
    ) {
        val articles = parseArticles(widgetData)
        val index = clamp(widgetData.getInt(KEY_INDEX, 0), articles.length())
        appWidgetIds.forEach { id ->
            appWidgetManager.updateAppWidget(id, buildViews(context, articles, index, id))
        }
    }

    override fun onReceive(context: Context, intent: Intent) {
        // 清單新→舊排（index 0 = 最新）。◀ 看更舊(+1)、▶ 看更新(-1)；不循環。
        when (intent.action) {
            ACTION_PREV -> shift(context, +1)
            ACTION_NEXT -> shift(context, -1)
        }
        super.onReceive(context, intent)
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

    /** 切換目前故事（不循環，夾在 [0, count-1]），更新 index 後重繪所有 widget。 */
    private fun shift(context: Context, delta: Int) {
        val data = prefs(context)
        val count = parseArticles(data).length()
        if (count == 0) return
        val cur = clamp(data.getInt(KEY_INDEX, 0), count)
        val next = (cur + delta).coerceIn(0, count - 1)
        if (next == cur) return
        data.edit().putInt(KEY_INDEX, next).apply()

        val mgr = AppWidgetManager.getInstance(context)
        val ids = mgr.getAppWidgetIds(ComponentName(context, HSStoryWidgetProvider::class.java))
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
            views.setTextViewText(R.id.widget_pos, "")
            showPlainBody(views, "開啟 App 載入最新故事")
            views.setOnClickPendingIntent(R.id.widget_root, launchApp(context, 300 + widgetId, null))
            return views
        }

        val a = articles.getJSONObject(index)
        views.setTextViewText(R.id.widget_title, a.optString("title", "聖靈故事"))
        views.setTextViewText(R.id.widget_pos, "${index + 1}/${articles.length()}")

        val body = stripMarkdown(a.optString("body", ""))
        setBody(context, views, if (body.isNotBlank()) body else a.optString("excerpt", ""))

        val flags = PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        val url = a.optString("url", "")
        if (url.isNotEmpty()) {
            val view = Intent(Intent.ACTION_VIEW, Uri.parse(url))
            views.setOnClickPendingIntent(
                R.id.widget_root, PendingIntent.getActivity(context, 100 + widgetId, view, flags)
            )
        }
        val last = articles.length() - 1
        // ◀ 看更舊：在最舊停用；▶ 看更新：在最新（index 0）停用。不循環。
        navButton(context, views, R.id.widget_prev, ACTION_PREV, 1, index < last)
        navButton(context, views, R.id.widget_next, ACTION_NEXT, 2, index > 0)
        return views
    }

    /** 設定切換鍵：可用則綁點擊 + 正常色；停用則清點擊 + 淡色。 */
    private fun navButton(
        context: Context,
        views: RemoteViews,
        viewId: Int,
        action: String,
        req: Int,
        enabled: Boolean
    ) {
        views.setInt(viewId, "setTextColor", if (enabled) 0xFF2B2620.toInt() else 0xFFCBC4B6.toInt())
        views.setOnClickPendingIntent(viewId, if (enabled) broadcast(context, action, req) else null)
    }

    /**
     * 顯示內文。API 31+ 用可捲動 ListView（逐段一列，直接把列塞進 RemoteViews，
     * 不走 RemoteViewsService）；舊系統退回不可捲的 TextView。
     */
    private fun setBody(context: Context, views: RemoteViews, text: String) {
        val paras = text.split(Regex("\n+")).map { it.trim() }.filter { it.isNotEmpty() }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S && paras.isNotEmpty()) {
            val builder = RemoteViews.RemoteCollectionItems.Builder()
            paras.forEachIndexed { i, p ->
                val row = RemoteViews(context.packageName, R.layout.widget_body_row)
                row.setTextViewText(R.id.widget_body_line, p)
                builder.addItem(i.toLong(), row)
            }
            builder.setViewTypeCount(1)
            builder.setHasStableIds(true)
            views.setRemoteAdapter(R.id.widget_body_list, builder.build())
            views.setViewVisibility(R.id.widget_body_list, View.VISIBLE)
            views.setViewVisibility(R.id.widget_body, View.GONE)
        } else {
            showPlainBody(views, text)
        }
    }

    private fun showPlainBody(views: RemoteViews, text: String) {
        views.setTextViewText(R.id.widget_body, text)
        views.setViewVisibility(R.id.widget_body, View.VISIBLE)
        views.setViewVisibility(R.id.widget_body_list, View.GONE)
    }

    private fun broadcast(context: Context, action: String, req: Int): PendingIntent {
        val intent = Intent(context, HSStoryWidgetProvider::class.java).setAction(action)
        val flags = PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        return PendingIntent.getBroadcast(context, req, intent, flags)
    }

    /**
     * 開啟 App 的 PendingIntent（自建）。沿用 home_widget 的 LAUNCH action 讓 App 端
     * widgetClicked 收得到 uri；不用外掛的 HomeWidgetLaunchIntent，以避開它在
     * Android 15+（SDK 35+）設 pendingIntentBackgroundActivityStartMode 造成的崩潰。
     */
    private fun launchApp(context: Context, req: Int, uri: Uri?): PendingIntent {
        val intent = Intent(context, MainActivity::class.java).apply {
            action = LAUNCH_ACTION
            data = uri
        }
        val flags = PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        return PendingIntent.getActivity(context, req, intent, flags)
    }

    /** 去掉常見 Markdown 標記，讓 widget 內文以純文字呈現。 */
    private fun stripMarkdown(md: String): String = md
        .replace(Regex("!\\[[^\\]]*\\]\\([^)]*\\)"), "")
        .replace(Regex("\\[([^\\]]*)\\]\\([^)]*\\)"), "$1")
        .replace(Regex("(?m)^\\s{0,3}#{1,6}\\s*"), "")
        .replace(Regex("(?m)^\\s{0,3}[-*+]\\s+"), "")
        .replace(Regex("(?m)^\\s{0,3}>\\s?"), "")
        .replace(Regex("[*`_]"), "")
        .trim()
}

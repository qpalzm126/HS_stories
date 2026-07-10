package com.hsstory.hs_story_app

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.net.Uri
import android.widget.RemoteViews
import es.antonborri.home_widget.HomeWidgetProvider

/**
 * 聖靈故事 Android 桌面 Widget。
 *
 * 資料來源：Flutter 端 home_widget 寫入的 SharedPreferences（key 對應 lib/config.dart 的 Config.k*）。
 * 點擊整個 widget → 以 ACTION_VIEW 開啟該篇文章網址。
 *
 * 已於 AndroidManifest.xml 註冊為 <receiver>，res/xml/hs_story_widget_info.xml 定義外觀。
 */
class HSStoryWidgetProvider : HomeWidgetProvider() {
    override fun onUpdate(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetIds: IntArray,
        widgetData: SharedPreferences
    ) {
        appWidgetIds.forEach { widgetId ->
            val views = RemoteViews(context.packageName, R.layout.hs_story_widget).apply {
                val title = widgetData.getString("hs_title", "聖靈故事") ?: "聖靈故事"
                val excerpt = widgetData.getString("hs_excerpt", "開啟 App 載入最新故事") ?: ""
                val url = widgetData.getString("hs_url", null)

                setTextViewText(R.id.widget_title, title)
                setTextViewText(R.id.widget_excerpt, excerpt)

                if (!url.isNullOrEmpty()) {
                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                    val flags = PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
                    val pending = PendingIntent.getActivity(context, widgetId, intent, flags)
                    setOnClickPendingIntent(R.id.widget_root, pending)
                }
            }
            appWidgetManager.updateAppWidget(widgetId, views)
        }
    }
}

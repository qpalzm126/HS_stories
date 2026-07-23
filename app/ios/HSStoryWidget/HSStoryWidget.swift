//
//   HSStoryWidget.swift
//  Runner
//
//  Created by Leon.Chen on 2026/7/23.
//
// 聖靈故事 iOS 桌面 Widget（WidgetKit / SwiftUI）
//
// 資料來源：Flutter 端 home_widget 透過 App Group 寫入的 UserDefaults。
// 鍵名對應 app/lib/config.dart 的 Config.k*（hs_title / hs_excerpt / hs_url / hs_published_at）。
//
// 接線（見 app/README.md）：
//  1. Xcode 新增 Widget Extension target，命名 kind 為 "HSStoryWidget"
//     （對應 Config.iOSWidgetName）。
//  2. 主 App 與 Widget Extension 都加入同一個 App Group：group.com.hsstory.app
//     （對應 Config.appGroupId）。
//  3. 用本檔內容取代 Xcode 產生的 widget 樣板。

import WidgetKit
import SwiftUI

private let appGroupId = "group.com.hsstory.app"

private enum Keys {
    static let title = "hs_title"
    static let excerpt = "hs_excerpt"
    static let url = "hs_url"
    static let publishedAt = "hs_published_at"
}

struct StoryEntry: TimelineEntry {
    let date: Date
    let title: String
    let excerpt: String
    let url: URL?
}

struct Provider: TimelineProvider {
    private func loadEntry() -> StoryEntry {
        let defaults = UserDefaults(suiteName: appGroupId)
        let title = defaults?.string(forKey: Keys.title) ?? "聖靈故事"
        let excerpt = defaults?.string(forKey: Keys.excerpt) ?? "開啟 App 載入最新故事"
        let urlStr = defaults?.string(forKey: Keys.url) ?? ""
        return StoryEntry(
            date: Date(),
            title: title,
            excerpt: excerpt,
            url: urlStr.isEmpty ? nil : URL(string: urlStr)
        )
    }

    func placeholder(in context: Context) -> StoryEntry {
        StoryEntry(date: Date(), title: "聖靈故事",
                   excerpt: "每日一篇見證與分享", url: nil)
    }

    func getSnapshot(in context: Context, completion: @escaping (StoryEntry) -> Void) {
        completion(loadEntry())
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<StoryEntry>) -> Void) {
        let entry = loadEntry()
        // App 端會在抓到新文章時主動 reload；此處另設 1 小時後備刷新。
        let next = Calendar.current.date(byAdding: .hour, value: 1, to: Date())!
        completion(Timeline(entries: [entry], policy: .after(next)))
    }
}

struct HSStoryWidgetEntryView: View {
    var entry: Provider.Entry
    @Environment(\.widgetFamily) var family

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("聖靈故事")
                .font(.caption2)
                .foregroundColor(.secondary)
            Text(entry.title)
                .font(.headline)
                .lineLimit(family == .systemSmall ? 3 : 2)
            if family != .systemSmall {
                Text(entry.excerpt)
                    .font(.footnote)
                    .foregroundColor(.secondary)
                    .lineLimit(3)
            }
            Spacer(minLength: 0)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .padding(12)
        // 點擊整個 widget → 開啟該篇文章網址（外部瀏覽器）。
        .widgetURL(entry.url)
    }
}

@main
struct HSStoryWidget: Widget {
    let kind: String = "HSStoryWidget"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: Provider()) { entry in
            if #available(iOS 17.0, *) {
                HSStoryWidgetEntryView(entry: entry)
                    .containerBackground(.fill.tertiary, for: .widget)
            } else {
                HSStoryWidgetEntryView(entry: entry)
                    .padding()
                    .background()
            }
        }
        .configurationDisplayName("聖靈故事")
        .description("顯示最新一篇聖靈故事，點擊閱讀全文。")
        .supportedFamilies([.systemSmall, .systemMedium])
    }
}


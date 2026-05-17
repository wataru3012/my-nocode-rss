import fs from "fs";
import axios from "axios";
import * as cheerio from "cheerio";

function toRSS(feed, items) {
  let xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>${feed.title}</title>
<link>${feed.url}</link>
<description>RSS Feed</description>
`;

  for (const item of items) {
    xml += `
<item>
<title><![CDATA[${item.title}]]></title>
<link>${item.link}</link>
</item>`;
  }

  xml += `
</channel>
</rss>`;

  return xml;
}

async function run() {
  const config = JSON.parse(fs.readFileSync("./config.json"));

  fs.mkdirSync("./dist", { recursive: true });

  for (const feed of config.feeds) {
    const html = (await axios.get(feed.url)).data;
    const $ = cheerio.load(html);

    const items = [];

    $(feed.itemSelector).each((_, el) => {
      const title = $(el).find(feed.titleSelector).text().trim();
      let link = $(el).find(feed.linkSelector).attr("href");

      if (title && link) {
        link = new URL(link, feed.url).toString();
        items.push({ title, link });
      }
    });

    const rss = toRSS(feed, items);

    fs.writeFileSync(`./dist/${feed.id}.xml`, rss);
  }

  console.log("done");
}

run();

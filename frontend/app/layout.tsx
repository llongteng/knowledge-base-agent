import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "智能知识库问答 Agent",
  description: "面向企业知识库的可信问答 Agent，回答可追溯到原文来源。",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}

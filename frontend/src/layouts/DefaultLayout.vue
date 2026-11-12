<template>
  <el-container class="layout">
    <el-aside width="200px" class="aside">
      <div class="brand">
        <span class="brand-name">AI-WorkBench</span>
      </div>
      <el-menu router :default-active="$route.path" class="menu">
        <el-menu-item index="/image-gen">
          <el-icon><Picture /></el-icon>
          <span>图像生成</span>
        </el-menu-item>
        <el-menu-item index="/somark">
          <el-icon><Document /></el-icon>
          <span>文档解析</span>
        </el-menu-item>
        <el-menu-item index="/text-clean">
          <el-icon><Brush /></el-icon>
          <span>文本清洗</span>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <span>设置</span>
        </el-menu-item>
      </el-menu>
      <div class="aside-footer mono">AI-WorkBench v0.1</div>
    </el-aside>
    <el-main class="main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { Brush, Document, Picture, Setting } from '@element-plus/icons-vue'
</script>

<style scoped>
.layout {
  height: 100%;
}

.aside {
  background: #fff;
  border-right: 1px solid #ebeef5;
  display: flex;
  flex-direction: column;
}

.brand {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid #ebeef5;
}

.brand-name {
  font-size: 17px;
  font-weight: 700;
  color: var(--el-color-primary);
  letter-spacing: 0.5px;
}

.menu {
  border-right: none;
  flex: 1;
}

.aside-footer {
  padding: 12px;
  text-align: center;
  color: #c0c4cc;
}

.main {
  padding: 20px;
  overflow-y: auto;
}
</style>

<template>
  <div id="app">
    <el-container>
      <el-aside width="200px">
        <div class="logo">
          <h3>小说管理系统</h3>
        </div>
        <el-menu
          :default-active="currentRoute"
          router
          class="el-menu-vertical"
        >
          <el-menu-item index="/novels">
            <span>小说管理</span>
          </el-menu-item>
          <el-menu-item index="/novel-names">
            <span>小说名管理</span>
          </el-menu-item>
          <el-menu-item index="/roles">
            <span>角色管理</span>
          </el-menu-item>
          <el-menu-item index="/role-audios">
            <span>角色音频管理</span>
          </el-menu-item>
          <el-menu-item index="/settings">
            <span>系统设置</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      <el-container>
        <el-main>
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const currentRoute = computed(() => route.path)
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  height: 100%;
  width: 100%;
}

#app {
  height: 100vh;
  width: 100vw;
}

.el-container {
  height: 100%;
}

.el-aside {
  background-color: #304156;
  color: #fff;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #263445;
}

.logo h3 {
  color: #fff;
  font-size: 18px;
  font-weight: 600;
}

.el-menu-vertical {
  border-right: none;
  background-color: #304156;
}

.el-menu-item {
  color: #bfcbd9;
}

.el-menu-item:hover,
.el-menu-item.is-active {
  background-color: #263445 !important;
  color: #409eff;
}

.el-main {
  background-color: #f0f2f5;
  padding: 0;
}
</style>

<template>
  <div id="app">
    <!-- 路由视图：显示当前路由对应的页面组件 -->
    <router-view />
  </div>
</template>

<script setup>
// 这是 Vue 3 的 Composition API 写法
// 相当于 React 的函数组件
</script>

<style>
/* 全局样式 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>

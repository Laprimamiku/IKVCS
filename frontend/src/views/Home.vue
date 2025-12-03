<template>
  <div class="home">
    <h1>IKVCS - 智能知识型视频社区</h1>
    <p>欢迎来到 IKVCS！</p>
    <el-button type="primary" @click="goToLogin">登录</el-button>
    <el-button @click="goToRegister">注册</el-button>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const goToLogin = () => {
  router.push('/login')
}

const goToRegister = () => {
  router.push('/register')
}
</script>

<style scoped>
.home {
  text-align: center;
  padding: 50px;
}

h1 {
  color: #409EFF;
  margin-bottom: 20px;
}
</style>

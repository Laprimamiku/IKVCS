/**
 * 用户状态管理
 * 
 * 这个文件管理用户相关的状态（登录状态、用户信息等）
 * 相当于 Vuex 的 Store
 * 
 * 类比 Java：
 *   相当于 Spring 的 Service + 内存缓存
 */
import { defineStore } from 'pinia'
import { login as loginApi, register as registerApi, logout as logoutApi, getCurrentUser } from '@/api/auth'

export const useUserStore = defineStore('user', {
  // 状态（相当于 Java 的成员变量）
  state: () => ({
    token: localStorage.getItem('access_token') || '',
    userInfo: null
  }),
  
  // 计算属性（相当于 Java 的 getter 方法）
  getters: {
    // 是否已登录
    isLoggedIn: (state) => !!state.token,
    
    // 是否是管理员
    isAdmin: (state) => state.userInfo?.role === 'admin',
    
    // 用户昵称
    nickname: (state) => state.userInfo?.nickname || '游客',
    
    // 用户头像
    avatar: (state) => state.userInfo?.avatar || 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png'
  },
  
  // 方法（相当于 Java 的方法）
  actions: {
    /**
     * 登录
     * 
     * @param {string} username - 用户名
     * @param {string} password - 密码
     * 
     * 流程：
     * 1. 调用登录 API
     * 2. 保存 JWT 令牌到 localStorage
     * 3. 获取用户信息
     * 
     * 为什么这样写：
     *   登录成功后立即获取用户信息
     *   这样可以在页面上显示用户昵称、头像等
     */
    async login(username, password) {
      try {
        // 1. 调用登录 API
        const res = await loginApi({ username, password })
        
        // 2. 保存令牌
        this.token = res.access_token
        localStorage.setItem('access_token', res.access_token)
        
        // 3. 获取用户信息
        await this.fetchUserInfo()
        
        return res
      } catch (error) {
        console.error('登录失败:', error)
        throw error
      }
    },
    
    /**
     * 注册
     * 
     * @param {string} username - 用户名
     * @param {string} password - 密码
     * @param {string} nickname - 昵称
     * 
     * 流程：
     * 1. 调用注册 API
     * 2. 注册成功后自动登录
     * 
     * 为什么这样写：
     *   注册成功后自动登录，提升用户体验
     *   用户不需要再次输入用户名密码
     */
    async register(username, password, nickname) {
      try {
        // 1. 调用注册 API
        await registerApi({ username, password, nickname })
        
        // 2. 注册成功后自动登录
        await this.login(username, password)
      } catch (error) {
        console.error('注册失败:', error)
        throw error
      }
    },
    
    /**
     * 获取用户信息
     * 
     * 使用场景：
     * 1. 登录成功后获取用户信息
     * 2. 页面刷新后恢复用户信息
     * 3. 更新用户信息后刷新
     */
    async fetchUserInfo() {
      try {
        const res = await getCurrentUser()
        this.userInfo = res
        return res
      } catch (error) {
        console.error('获取用户信息失败:', error)
        // 如果获取失败，清空令牌（可能令牌已过期）
        this.token = ''
        localStorage.removeItem('access_token')
        throw error
      }
    },
    
    /**
     * 登出
     * 
     * 流程：
     * 1. 调用登出 API（将令牌加入黑名单）
     * 2. 清空本地状态和 localStorage
     * 
     * 为什么这样写：
     *   即使 API 调用失败，也要清空本地状态
     *   这样可以确保用户能够登出
     */
    async logout() {
      try {
        // 1. 调用登出 API
        await logoutApi()
      } catch (error) {
        console.error('登出失败:', error)
        // 即使 API 失败，也继续清空本地状态
      } finally {
        // 2. 清空状态
        this.token = ''
        this.userInfo = null
        localStorage.removeItem('access_token')
      }
    },
    
    /**
     * 初始化用户信息
     * 
     * 使用场景：
     *   页面刷新后，如果 localStorage 中有令牌
     *   自动获取用户信息，恢复登录状态
     */
    async initUserInfo() {
      if (this.token) {
        try {
          await this.fetchUserInfo()
        } catch (error) {
          // 令牌可能已过期，清空状态
          this.token = ''
          this.userInfo = null
          localStorage.removeItem('access_token')
        }
      }
    }
  }
})

/**
 * 用户状态管理
 * 
 * 这个文件管理用户相关的状态（登录状态、用户信息等）
 * 相当于 Vuex 的 Store
 */
import { defineStore } from 'pinia'
import request from '../utils/request'

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
    nickname: (state) => state.userInfo?.nickname || '游客'
  },
  
  // 方法（相当于 Java 的方法）
  actions: {
    /**
     * 登录
     * @param {string} username - 用户名
     * @param {string} password - 密码
     */
    async login(username, password) {
      try {
        const res = await request.post('/auth/login', {
          username,
          password
        })
        
        // 保存令牌
        this.token = res.access_token
        localStorage.setItem('access_token', res.access_token)
        
        // 获取用户信息
        await this.fetchUserInfo()
        
        return res
      } catch (error) {
        console.error('登录失败:', error)
        throw error
      }
    },
    
    /**
     * 注册
     * @param {string} username - 用户名
     * @param {string} password - 密码
     * @param {string} nickname - 昵称
     */
    async register(username, password, nickname) {
      try {
        await request.post('/auth/register', {
          username,
          password,
          nickname
        })
        
        // 注册成功后自动登录
        await this.login(username, password)
      } catch (error) {
        console.error('注册失败:', error)
        throw error
      }
    },
    
    /**
     * 获取用户信息
     */
    async fetchUserInfo() {
      try {
        const res = await request.get('/users/me')
        this.userInfo = res
        return res
      } catch (error) {
        console.error('获取用户信息失败:', error)
        throw error
      }
    },
    
    /**
     * 登出
     */
    async logout() {
      try {
        await request.post('/auth/logout')
      } catch (error) {
        console.error('登出失败:', error)
      } finally {
        // 清空状态
        this.token = ''
        this.userInfo = null
        localStorage.removeItem('access_token')
      }
    }
  }
})

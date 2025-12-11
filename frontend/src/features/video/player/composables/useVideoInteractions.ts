import { ref } from 'vue';
import { ElMessage } from 'element-plus';
import { useUserStore } from "@/shared/stores/user";

export function useVideoInteractions() {
  const userStore = useUserStore();
  const isLiked = ref(false);
  const isCollected = ref(false);

  const handleLike = () => {
    if (!userStore.isLoggedIn) {
      ElMessage.warning('请先登录');
      return false;
    }
    isLiked.value = !isLiked.value;
    ElMessage.success(isLiked.value ? '点赞成功' : '取消点赞');
    return true;
  };

  const handleCollect = () => {
    if (!userStore.isLoggedIn) {
      ElMessage.warning('请先登录');
      return false;
    }
    isCollected.value = !isCollected.value;
    ElMessage.success(isCollected.value ? '收藏成功' : '取消收藏');
    return true;
  };

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href);
    ElMessage.success('链接已复制到剪贴板');
  };

  return {
    isLiked,
    isCollected,
    handleLike,
    handleCollect,
    handleShare,
  };
}

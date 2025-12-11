<template>
  <el-form
    ref="formRef"
    :model="localForm"
    :rules="rules"
    label-width="100px"
    class="video-info-form"
  >
    <el-form-item label="视频标题" prop="title">
      <el-input
        v-model="localForm.title"
        placeholder="请输入视频标题"
        maxlength="100"
        show-word-limit
      />
    </el-form-item>

    <el-form-item label="视频描述" prop="description">
      <el-input
        v-model="localForm.description"
        type="textarea"
        :rows="5"
        placeholder="请输入视频描述"
        maxlength="500"
        show-word-limit
      />
    </el-form-item>

    <el-form-item label="视频分类" prop="category_id">
      <el-select
        v-model="localForm.category_id"
        placeholder="请选择分类"
        clearable
        style="width: 100%"
      >
        <el-option
          v-for="cat in categories"
          :key="cat.id"
          :label="cat.name"
          :value="cat.id"
        />
      </el-select>
    </el-form-item>
  </el-form>
</template>

<script setup lang="ts">
import { ref, watch, reactive } from "vue";
import type { FormInstance, FormRules } from "element-plus";
import type { Category } from "@/shared/types/entity";

const props = defineProps<{
  categories: Category[];
  modelValue: {
    title: string;
    description: string;
    category_id: number | null;
  };
}>();

const emit = defineEmits<{
  "update:modelValue": [value: typeof props.modelValue];
}>();

const formRef = ref<FormInstance | null>(null);

// 使用reactive对象实现双向绑定，Element Plus表单需要reactive对象
const localForm = reactive({
  title: props.modelValue.title,
  description: props.modelValue.description,
  category_id: props.modelValue.category_id,
});

// 监听props变化，同步到localForm（用于父组件重置表单等情况）
watch(
  () => props.modelValue,
  (newValue) => {
    if (
      localForm.title !== newValue.title ||
      localForm.description !== newValue.description ||
      localForm.category_id !== newValue.category_id
    ) {
      localForm.title = newValue.title;
      localForm.description = newValue.description;
      localForm.category_id = newValue.category_id;
    }
  },
  { deep: true }
);

// 监听localForm变化，同步到父组件
watch(
  localForm,
  (newValue) => {
    emit("update:modelValue", {
      title: newValue.title,
      description: newValue.description,
      category_id: newValue.category_id,
    });
  },
  { deep: true }
);

const rules: FormRules = {
  title: [
    { required: true, message: "请输入视频标题", trigger: "blur" },
    {
      min: 1,
      max: 100,
      message: "标题长度在 1 到 100 个字符",
      trigger: "blur",
    },
  ],
  description: [
    { max: 500, message: "描述长度不能超过 500 个字符", trigger: "blur" },
  ],
  category_id: [
    { required: true, message: "请选择视频分类", trigger: "change" },
  ],
};

// 暴露验证方法
defineExpose({
  validate: () => formRef.value?.validate(),
  resetFields: () => formRef.value?.resetFields(),
});
</script>

<style lang="scss" scoped>
.video-info-form {
  max-width: 600px;
  margin: 0 auto;
}
</style>
